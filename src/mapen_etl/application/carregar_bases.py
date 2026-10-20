"""Caso de uso do ETL: Extract das duas bases, Transform e so entao Load, para uma falta nao deixar carga pela metade."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from mapen_etl.application.portas import ExtractPort, LoadPort
from mapen_etl.application.transform import Transform
from mapen_etl.domain.bases import BASES, ModoCarga

T = TypeVar("T")


def carregar_bases(
    extract: ExtractPort[T],
    transform: Transform,
    load: LoadPort[T],
    diretorio: Path,
    modo: ModoCarga,
) -> dict[str, int]:
    """Devolve {tabela: linhas gravadas}. Ausencia de arquivo aborta antes de gravar qualquer tabela."""
    prontas: list[tuple[str, T]] = []
    for base in BASES:
        caminho = diretorio / base.arquivo
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo obrigatorio do ETL nao encontrado: '{caminho}'.")
        print(f"Extract: {caminho}")
        bruto = extract.extract(base, caminho)
        prontas.append((base.tabela, transform.transform_data(bruto)))
    resultado: dict[str, int] = {}
    for tabela, conteudo in prontas:
        print(f"Load: tabela '{tabela}' (Neon)")
        resultado[tabela] = load.load_neon(conteudo, tabela, modo)
    return resultado
