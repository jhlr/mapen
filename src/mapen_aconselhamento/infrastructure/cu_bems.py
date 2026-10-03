"""Carregador do CU-BEMS (CSV de andar, 1 min) para a tabela `leitura`."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

from mapen_aconselhamento.domain.calendario import DUPLICADOS_ERRO, reindexar, tratar_duplicados
from mapen_aconselhamento.infrastructure.duckdb_leituras import inserir_leituras

_COLUNA_KW = re.compile(r"^(z\d+_(?:AC\d+|Light|Plug))\(kW\)$")


def carregar_cu_bems(
    con: duckdb.DuckDBPyConnection,
    csv: Path,
    sensor_id: str,
    inicio: pd.Timestamp | None = None,
    fim: pd.Timestamp | None = None,
    duplicados: str = DUPLICADOS_ERRO,
) -> int:
    """Carrega um CSV de andar do CU-BEMS (1 min, kW por AC/iluminacao/tomadas de cada zona).

    `fim` e exclusivo. Colunas ambientais (temperatura, umidade, lux) sao ignoradas.
    `equipamento_id` e o nome da coluna sem unidade (ex.: `z2_AC1`). Devolve linhas inseridas.
    `duplicados`: `erro` (padrao) ou `primeiro` (ver `tratar_duplicados`).
    """
    cabecalho = pd.read_csv(csv, nrows=0).columns
    mapa = {c: m.group(1) for c in cabecalho if (m := _COLUNA_KW.match(c))}
    bruto = pd.read_csv(csv, usecols=["Date", *mapa], parse_dates=["Date"], index_col="Date")
    bruto = bruto.rename(columns=mapa)
    if inicio is not None and fim is not None:
        bruto = bruto[(bruto.index >= inicio) & (bruto.index < fim)]
    unico, repetidos = tratar_duplicados(bruto, duplicados)
    completo = reindexar(unico, "1min", inicio, fim)
    return inserir_leituras(con, completo, sensor_id, "1min", 1000.0, repetidos, duplicados)
