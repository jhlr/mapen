"""Relatorio do que o dispositivo registrou e do que o servidor confirmou. Lacunas sao mostradas, nunca preenchidas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_simulador.domain.eventos import EventoDispositivo


@dataclass(frozen=True)
class Lacuna:
    """Entre duas amostras registradas consecutivas (relogio do dispositivo)."""

    inicio: datetime
    fim: datetime
    amostras_faltantes: int


@dataclass(frozen=True)
class RelatorioSimulacao:
    amostras_registradas: int
    amostras_confirmadas: int
    amostras_perdidas_overflow: int
    pendentes_no_fim: int
    envios_tentados: int
    envios_falhos: int
    eventos: tuple[EventoDispositivo, ...]
    lacunas: tuple[Lacuna, ...]
    lotes_confirmados: tuple[str, ...]
    eventos_confirmados: int = 0
    eventos_nao_confirmados: int = 0


def calcular_lacunas(instantes: list[datetime], passo: timedelta) -> tuple[Lacuna, ...]:
    """Buraco = diferenca entre registros consecutivos maior que 1,5 passo. Nada e interpolado."""
    lacunas: list[Lacuna] = []
    for anterior, seguinte in zip(instantes, instantes[1:], strict=False):
        if seguinte - anterior > passo * 1.5:
            lacunas.append(Lacuna(anterior, seguinte, round((seguinte - anterior) / passo) - 1))
    return tuple(lacunas)
