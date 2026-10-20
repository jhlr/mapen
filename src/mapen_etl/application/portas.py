"""Portas do ETL. O conteudo lido e opaco para a aplicacao (`T`): quem le e quem grava combinam o tipo."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeVar

from mapen_etl.domain.bases import BaseAv1, ModoCarga

T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


class LeitorBase(Protocol[T_co]):
    def ler(self, base: BaseAv1, caminho: Path) -> T_co: ...


class GravadorTabela(Protocol[T_contra]):
    def gravar(self, conteudo: T_contra, tabela: str, modo: ModoCarga) -> int: ...
