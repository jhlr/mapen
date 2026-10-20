"""Leitura dos CSVs da AV1 com a procedencia de cada linha (`source_file`, `source_row`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from mapen_etl.domain.bases import BaseAv1

RESERVADAS = frozenset({"source_file", "source_row"})


class LeitorCsv:
    def ler(self, base: BaseAv1, caminho: Path) -> pd.DataFrame:
        df = pd.read_csv(caminho, encoding="utf-8-sig", parse_dates=list(base.colunas_data))
        if df.empty:
            raise ValueError(f"A origem '{caminho}' nao contem linhas para carregar.")
        conflito = RESERVADAS & set(df.columns)
        if conflito:
            raise ValueError(f"'{caminho}' contem colunas reservadas pelo ETL: {', '.join(sorted(conflito))}.")
        df.insert(0, "source_row", range(1, len(df) + 1))
        df.insert(0, "source_file", caminho.name)
        return df
