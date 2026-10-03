"""Fuso das instalacoes. A tabela `leitura` guarda hora local ingenua (como no M1); a API so fala em datas com fuso."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from mapen_plataforma.domain.entidades import ErroDominio

FUSO_LOCAL = ZoneInfo("America/Recife")


def exigir_fuso(valor: datetime, campo: str) -> datetime:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ErroDominio(f"{campo} deve ter fuso horario")
    return valor


def para_local_ingenuo(valor: datetime, campo: str = "data") -> datetime:
    """Instante com fuso -> hora local ingenua (a forma gravada em `leitura`)."""
    return exigir_fuso(valor, campo).astimezone(FUSO_LOCAL).replace(tzinfo=None)


def de_local_ingenuo(valor: datetime) -> datetime:
    """Hora local ingenua gravada -> instante com fuso."""
    return valor.replace(tzinfo=FUSO_LOCAL)
