"""Armazenamento DuckDB das leituras: esquema, insercao e consultas da tabela `leitura`.

Pontos que faltam no calendario viram NULL com `ausente = TRUE`. A quantidade de timestamps
duplicados descartados fica na tabela `ingestao` (e sai no relatorio).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

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

DDL_INGESTAO = """
CREATE TABLE IF NOT EXISTS ingestao (
    sensor_id VARCHAR,
    duplicados BIGINT,
    politica_duplicados VARCHAR
)
"""


def conectar(caminho: str | Path = ":memory:") -> duckdb.DuckDBPyConnection:
    """Abre o DuckDB e garante a tabela `leitura`."""
    con = duckdb.connect(str(caminho))
    con.execute(DDL_LEITURA)
    con.execute(DDL_INGESTAO)
    return con


def inserir_leituras(
    con: duckdb.DuckDBPyConnection,
    largo_kw: pd.DataFrame,
    sensor_id: str,
    freq: str,
    fator_para_w: float,
    duplicados: int,
    politica: str,
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
    con.execute("DELETE FROM ingestao WHERE sensor_id = ?", [sensor_id])
    con.execute("INSERT INTO ingestao VALUES (?, ?, ?)", [sensor_id, duplicados, politica])
    return len(tabela)


def ler_leituras(
    con: duckdb.DuckDBPyConnection, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp
) -> pd.DataFrame:
    """Leituras de um predio em [inicio, fim): colunas ts, equipamento_id, kwh, ausente."""
    return con.execute(
        "SELECT ts, equipamento_id, kwh, ausente FROM leitura "
        "WHERE sensor_id = ? AND ts >= ? AND ts < ? ORDER BY equipamento_id, ts",
        [sensor_id, inicio.to_pydatetime(), fim.to_pydatetime()],
    ).df()


def ler_duplicados(con: duckdb.DuckDBPyConnection, sensor_id: str) -> tuple[int, str] | None:
    """(timestamps duplicados descartados, politica) da ultima carga do predio, ou None."""
    linha = con.execute(
        "SELECT duplicados, politica_duplicados FROM ingestao WHERE sensor_id = ?", [sensor_id]
    ).fetchone()
    if linha is None:
        return None
    return int(linha[0]), str(linha[1])


class LeiturasDuckDB:
    """Adaptador da porta `RepositorioLeituras` sobre uma conexao DuckDB."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def ler_leituras(self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
        return ler_leituras(self._con, sensor_id, inicio, fim)

    def ler_duplicados(self, sensor_id: str) -> tuple[int, str] | None:
        return ler_duplicados(self._con, sensor_id)
