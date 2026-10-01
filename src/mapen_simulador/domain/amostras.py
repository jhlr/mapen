"""Amostra gravada no buffer local e lote enviado ao servidor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Amostra:
    """`seq` e o contador monotonico do dispositivo; `ts` vem do relogio do dispositivo."""

    seq: int
    ts: datetime
    equipamento: str
    potencia_w: float
    kwh: float


@dataclass(frozen=True)
class LoteLeituras:
    """Mesmo conteudo, mesmo id: reenviar um lote nao gera lote novo."""

    id: str
    amostras: tuple[Amostra, ...]

    @property
    def seq_ultima(self) -> int:
        return self.amostras[-1].seq
