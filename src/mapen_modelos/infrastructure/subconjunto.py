"""Subconjunto do CU-BEMS usado no M3, carregado com o carregador do M1 num DuckDB proprio.

Um andar, todos os equipamentos, [inicio, fim) em 1 minuto. A carga e reaproveitada: se o
DuckDB ja tem o periodo completo, nao recarrega.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from mapen_aconselhamento.domain.calendario import DUPLICADOS_PRIMEIRO
from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_aconselhamento.infrastructure.cu_bems import carregar_cu_bems
from mapen_aconselhamento.infrastructure.duckdb_leituras import conectar

DUCKDB_PADRAO = RAIZ / "data" / "m3" / "serie.duckdb"
CSV_PADRAO = RAIZ / "data" / "publicos" / "cu_bems" / "2018Floor2.csv"
SENSOR_PADRAO = "cu_bems_2018Floor2"


def abrir_subconjunto(
    destino: Path, csv: Path, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp
) -> duckdb.DuckDBPyConnection:
    """Abre (e carrega, se preciso) o subconjunto. Duplicados: mantem o primeiro (contado na tabela `ingestao`)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = conectar(destino)
    esperado = int((fim - inicio) / pd.Timedelta("1min"))
    linha = con.execute(
        "SELECT count(DISTINCT ts) FROM leitura WHERE sensor_id = ? AND ts >= ? AND ts < ?",
        [sensor_id, inicio.to_pydatetime(), fim.to_pydatetime()],
    ).fetchone()
    existente = int(linha[0]) if linha is not None else 0
    if existente != esperado:
        carregar_cu_bems(con, csv, sensor_id, inicio, fim, duplicados=DUPLICADOS_PRIMEIRO)
    return con
