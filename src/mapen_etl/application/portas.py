"""Portas do ETL. O conteudo lido e opaco para a aplicacao (`T`): Extract e Load combinam o tipo."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeVar

from mapen_etl.domain.bases import BaseAv1, ModoCarga

T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


class ExtractPort(Protocol[T_co]):
    def extract(self, base: BaseAv1, caminho: Path) -> T_co: ...


class LoadPort(Protocol[T_contra]):
    def load_neon(self, conteudo: T_contra, tabela: str, modo: ModoCarga) -> int: ...
