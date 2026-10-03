"""Leitor do CSV de tarifas: so I/O; as regras de vigencia e preco vivem no dominio."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from mapen_aconselhamento.domain.tarifa import Tarifas
from mapen_aconselhamento.infrastructure.caminhos import CSV_TARIFAS_PADRAO


def carregar_tarifas(
    caminho: Path = CSV_TARIFAS_PADRAO,
    referencia: date | None = None,
    hora_21_intermediaria: bool = False,
    gross_up: float | None = None,
    bandeira_rs_kwh: float | None = None,
) -> Tarifas:
    """Le o CSV e devolve as `Tarifas` vigentes em `referencia` (ver `Tarifas.de_tabela`)."""
    tabela = pd.read_csv(caminho, dtype={"modalidade": str, "posto": str})
    return Tarifas.de_tabela(tabela, referencia, hora_21_intermediaria, gross_up, bandeira_rs_kwh)
