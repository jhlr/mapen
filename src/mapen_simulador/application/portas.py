"""Portas do simulador: tudo que toca o mundo (relogio, rede, chaves, fonte de serie)."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Protocol

from mapen_plataforma.domain.comando import ComandoRele
from mapen_simulador.domain.amostras import LoteLeituras
from mapen_simulador.domain.carga import SerieCarga
from mapen_simulador.domain.eventos import EventoDispositivo


class Relogio(Protocol):
    def agora(self) -> datetime: ...


class GeradorNonce(Protocol):
    def novo(self) -> str: ...


class ProvedorChaves(Protocol):
    def chave(self, device_id: str) -> bytes: ...


class FonteSerie(Protocol):
    def carregar(self, equipamento: str, inicio: datetime, duracao: timedelta) -> SerieCarga: ...


class EnvioLeituras(Protocol):
    def enviar(self, lote: LoteLeituras) -> bool:
        """True so se o servidor confirmou o lote (so entao o dispositivo o apaga do buffer)."""
        ...


class EnvioEventos(Protocol):
    def enviar(self, eventos: Sequence[EventoDispositivo]) -> bool:
        """True so se o servidor confirmou os eventos (so entao o dispositivo os apaga da memoria)."""
        ...


@dataclass(frozen=True)
class RespostaComando:
    aceito: bool
    status: int
    motivo: str | None


class EnvioComando(Protocol):
    def enviar(
        self, comando: ComandoRele, equipamento_id: str, origem: str, regra_id: str | None
    ) -> RespostaComando: ...
