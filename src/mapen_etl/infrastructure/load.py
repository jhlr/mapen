"""Etapa Load: gravacao em PostgreSQL (Neon). A URL vem de `DATABASE_URL` (ambiente ou `.env`), nunca do codigo."""

from __future__ import annotations

import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from mapen_etl.domain.bases import ModoCarga

_NOME_TABELA = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_MODOS = ("fail", "append", "replace")


def _com_driver(url: str) -> str:
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo) :]
    return url


class Load:
    def __init__(self, url: str | None = None) -> None:
        load_dotenv()
        bruta = url or os.getenv("DATABASE_URL")
        if not bruta:
            raise ValueError("Configure DATABASE_URL no ambiente ou no arquivo .env para conectar ao Neon.")
        self._url = _com_driver(bruta)

    def load_neon(self, conteudo: pd.DataFrame, tabela: str, modo: ModoCarga) -> int:
        if not _NOME_TABELA.fullmatch(tabela):
            raise ValueError("O nome da tabela deve comecar por letra ou _ e ter so letras ASCII, numeros e _.")
        if modo not in _MODOS:
            raise ValueError("modo deve ser 'fail', 'append' ou 'replace'.")
        if conteudo.empty:
            raise ValueError("Nao ha dados para carregar.")
        engine = create_engine(self._url)
        try:
            return int(conteudo.to_sql(tabela, engine, if_exists=modo, index=False) or 0)
        finally:
            engine.dispose()
