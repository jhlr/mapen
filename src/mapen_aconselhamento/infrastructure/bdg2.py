"""Carregador do BDG2 (medidores de eletricidade horarios, lidos direto do zip)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pandas as pd

from mapen_aconselhamento.domain.calendario import DUPLICADOS_ERRO, reindexar, tratar_duplicados
from mapen_aconselhamento.infrastructure.duckdb_leituras import inserir_leituras

# O zip do Zenodo tem uma pasta raiz com hash (buds-lab-...-<hash>/), entao casa pelo sufixo.
BDG2_ELETRICIDADE = "data/meters/cleaned/electricity_cleaned.csv"


def carregar_bdg2(
    con: duckdb.DuckDBPyConnection,
    zip_caminho: Path,
    medidores: list[str],
    inicio: pd.Timestamp | None = None,
    fim: pd.Timestamp | None = None,
    duplicados: str = DUPLICADOS_ERRO,
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
    unico, repetidos = tratar_duplicados(bruto, duplicados)
    completo = reindexar(unico, "1h", inicio, fim)
    total = 0
    for medidor in medidores:
        # kWh por hora == kW medio; potencia_w = kWh/h * 1000.
        total += inserir_leituras(
            con,
            completo[[medidor]].rename(columns={medidor: "geral"}),
            medidor,
            "1h",
            1000.0,
            repetidos,
            duplicados,
        )
    return total
