"""Eventos que o dispositivo guarda em memoria nao volatil."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime


class TipoEvento(enum.StrEnum):
    ULTIMO_SUSPIRO = "ultimo_suspiro"
    QUEDA_ENERGIA = "queda_energia"
    FALHA_CONEXAO = "falha_conexao"


@dataclass(frozen=True)
class EventoDispositivo:
    """Instantes pelo RTC do dispositivo. `fim` e `duracao_s` ficam `None` quando o RTC nao sobreviveu."""

    tipo: TipoEvento
    inicio: datetime
    fim: datetime | None = None
    duracao_s: float | None = None
    bateria_esgotada: bool = False
