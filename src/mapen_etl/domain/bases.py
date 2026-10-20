"""As duas bases pre-tratadas da AV1 que o ETL leva ao Neon."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModoCarga = Literal["fail", "append", "replace"]


@dataclass(frozen=True)
class BaseAv1:
    arquivo: str
    tabela: str
    colunas_data: tuple[str, ...]


BASES: tuple[BaseAv1, ...] = (
    BaseAv1("base_diaria.csv", "base_diaria", ("data",)),
    BaseAv1("base_horaria.csv", "base_horaria", ("inicio_hora",)),
)
