"""Caso de uso: ler as duas bases e so entao gravar, para uma falta nao deixar carga pela metade."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from mapen_etl.application.portas import GravadorTabela, LeitorBase
from mapen_etl.domain.bases import BASES, ModoCarga

T = TypeVar("T")


def carregar_bases(
    leitor: LeitorBase[T],
    gravador: GravadorTabela[T],
    diretorio: Path,
    modo: ModoCarga,
) -> dict[str, int]:
    """Devolve {tabela: linhas gravadas}. Ausencia de arquivo aborta antes de gravar qualquer tabela."""
    lidas: list[tuple[str, T]] = []
    for base in BASES:
        caminho = diretorio / base.arquivo
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo obrigatorio do ETL nao encontrado: '{caminho}'.")
        lidas.append((base.tabela, leitor.ler(base, caminho)))
    return {tabela: gravador.gravar(conteudo, tabela, modo) for tabela, conteudo in lidas}
