"""Ingestao de datasets publicos para a tabela DuckDB `leitura`.

Cada serie e reindexada a um calendario completo; pontos que faltam viram NULL com
`ausente = TRUE`. Nunca ha interpolacao.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

# O zip do Zenodo tem uma pasta raiz com hash (buds-lab-...-<hash>/), entao casa pelo sufixo.
BDG2_ELETRICIDADE = "data/meters/cleaned/electricity_cleaned.csv"
_COLUNA_KW = re.compile(r"^(z\d+_(?:AC\d+|Light|Plug))\(kW\)$")

DDL_LEITURA = """
CREATE TABLE IF NOT EXISTS leitura (
    sensor_id VARCHAR,
    equipamento_id VARCHAR,
    ts TIMESTAMP,
    potencia_w DOUBLE,
    tensao_v DOUBLE,
    kwh DOUBLE,
    ausente BOOLEAN
)
"""


def conectar(caminho: str | Path = ":memory:") -> duckdb.DuckDBPyConnection:
    """Abre o DuckDB e garante a tabela `leitura`."""
    con = duckdb.connect(str(caminho))
    con.execute(DDL_LEITURA)
    return con


def calendario(
    inicio: pd.Timestamp, fim: pd.Timestamp, freq: str
) -> pd.DatetimeIndex:
    """Calendario completo [inicio, fim) na frequencia dada."""
    return pd.date_range(inicio, fim, freq=freq, inclusive="left")


def reindexar(
    dados: pd.DataFrame, freq: str, inicio: pd.Timestamp | None = None, fim: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Reindexa `dados` (indice temporal) ao calendario completo; lacunas ficam NaN.

    `fim` e exclusivo. Sem `inicio`/`fim`, usa o primeiro e o ultimo timestamp presentes.
    """
    unico = dados[~dados.index.duplicated(keep="first")].sort_index()
    if inicio is None:
        inicio = pd.Timestamp(unico.index.min())
    if fim is None:
        fim = pd.Timestamp(unico.index.max()) + pd.Timedelta(freq)
    return unico.reindex(calendario(inicio, fim, freq))


def defasar(serie: pd.Series[float], periodos: int, freq: str) -> pd.Series[float]:
    """Lag/shift em calendario completo: uma lacuna nao e pulada, o valor defasado dela e NaN."""
    return reindexar(serie.to_frame("v"), freq)["v"].shift(periodos)


def _inserir(
    con: duckdb.DuckDBPyConnection,
    largo_kw: pd.DataFrame,
    sensor_id: str,
    freq: str,
    fator_para_w: float,
) -> int:
    """Converte DataFrame largo (colunas = equipamentos, valores = potencia) em linhas `leitura`."""
    horas = pd.Timedelta(freq).total_seconds() / 3600.0
    largo_kw = largo_kw.rename_axis("ts")
    longo = largo_kw.reset_index().melt(
        id_vars="ts", var_name="equipamento_id", value_name="potencia"
    )
    potencia_w = longo["potencia"] * fator_para_w
    tabela = pd.DataFrame(
        {
            "sensor_id": sensor_id,
            "equipamento_id": longo["equipamento_id"],
            "ts": longo["ts"],
            "potencia_w": potencia_w,
            "tensao_v": pd.Series(float("nan"), index=longo.index),
            "kwh": potencia_w / 1000.0 * horas,
            "ausente": longo["potencia"].isna(),
        }
    )
    inicio = pd.Timestamp(largo_kw.index.min())
    fim = pd.Timestamp(largo_kw.index.max())
    con.execute(
        "DELETE FROM leitura WHERE sensor_id = ? AND ts BETWEEN ? AND ?",
        [sensor_id, inicio.to_pydatetime(), fim.to_pydatetime()],
    )
    con.register("nova_leitura", tabela)
    con.execute("INSERT INTO leitura SELECT * FROM nova_leitura")
    con.unregister("nova_leitura")
    return len(tabela)


def carregar_cu_bems(
    con: duckdb.DuckDBPyConnection,
    csv: Path,
    sensor_id: str,
    inicio: pd.Timestamp | None = None,
    fim: pd.Timestamp | None = None,
) -> int:
    """Carrega um CSV de andar do CU-BEMS (1 min, kW por AC/iluminacao/tomadas de cada zona).

    `fim` e exclusivo. Colunas ambientais (temperatura, umidade, lux) sao ignoradas.
    `equipamento_id` e o nome da coluna sem unidade (ex.: `z2_AC1`). Devolve linhas inseridas.
    """
    cabecalho = pd.read_csv(csv, nrows=0).columns
    mapa = {c: m.group(1) for c in cabecalho if (m := _COLUNA_KW.match(c))}
    bruto = pd.read_csv(csv, usecols=["Date", *mapa], parse_dates=["Date"], index_col="Date")
    bruto = bruto.rename(columns=mapa)
    if inicio is not None and fim is not None:
        bruto = bruto[(bruto.index >= inicio) & (bruto.index < fim)]
    completo = reindexar(bruto, "1min", inicio, fim)
    return _inserir(con, completo, sensor_id, "1min", fator_para_w=1000.0)


def carregar_bdg2(
    con: duckdb.DuckDBPyConnection,
    zip_caminho: Path,
    medidores: list[str],
    inicio: pd.Timestamp | None = None,
    fim: pd.Timestamp | None = None,
) -> int:
    """Carrega medidores de eletricidade (horario, kWh por hora) do BDG2 lendo direto do zip.

    Um medidor por predio: `sensor_id` = nome do medidor, `equipamento_id` = `geral`.
    """
    with zipfile.ZipFile(zip_caminho) as zf:
        membro = next(n for n in zf.namelist() if n.endswith(BDG2_ELETRICIDADE))
        with zf.open(membro) as arquivo:
            bruto = pd.read_csv(
                arquivo,
                usecols=["timestamp", *medidores],
                parse_dates=["timestamp"],
                index_col="timestamp",
            )
    if inicio is not None and fim is not None:
        bruto = bruto[(bruto.index >= inicio) & (bruto.index < fim)]
    completo = reindexar(bruto, "1h", inicio, fim)
    total = 0
    for medidor in medidores:
        # kWh por hora == kW medio; potencia_w = kWh/h * 1000.
        total += _inserir(
            con, completo[[medidor]].rename(columns={medidor: "geral"}), medidor, "1h", 1000.0
        )
    return total


def ler_leituras(
    con: duckdb.DuckDBPyConnection, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp
) -> pd.DataFrame:
    """Leituras de um predio em [inicio, fim): colunas ts, equipamento_id, kwh, ausente."""
    return con.execute(
        "SELECT ts, equipamento_id, kwh, ausente FROM leitura "
        "WHERE sensor_id = ? AND ts >= ? AND ts < ? ORDER BY equipamento_id, ts",
        [sensor_id, inicio.to_pydatetime(), fim.to_pydatetime()],
    ).df()
