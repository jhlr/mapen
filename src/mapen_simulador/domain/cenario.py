"""O mundo fisico do dispositivo: janelas de queda de Wi-Fi e de energia da rede, e a autonomia da bateria."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_plataforma.domain.tempo import exigir_fuso
from mapen_simulador.domain.erros import ErroSimulador


class Conectividade(enum.StrEnum):
    ONLINE = "online"
    WIFI_DOWN = "wifi_down"
    MAINS_DOWN = "mains_down"


@dataclass(frozen=True)
class Janela:
    """Intervalo [inicio, fim) em tempo real."""

    inicio: datetime
    fim: datetime

    def __post_init__(self) -> None:
        exigir_fuso(self.inicio, "inicio")
        exigir_fuso(self.fim, "fim")
        if self.fim <= self.inicio:
            raise ErroSimulador("janela deve ter fim depois do inicio")

    def contem(self, t: datetime) -> bool:
        return self.inicio <= t < self.fim


@dataclass(frozen=True)
class Cenario:
    janelas_wifi: tuple[Janela, ...] = ()
    janelas_energia: tuple[Janela, ...] = ()
    autonomia: timedelta = timedelta(0)

    def __post_init__(self) -> None:
        if self.autonomia < timedelta(0):
            raise ErroSimulador("autonomia da bateria nao pode ser negativa")

    def janela_wifi_em(self, t: datetime) -> Janela | None:
        return next((j for j in self.janelas_wifi if j.contem(t)), None)

    def janela_energia_em(self, t: datetime) -> Janela | None:
        return next((j for j in self.janelas_energia if j.contem(t)), None)

    def conectividade_em(self, t: datetime) -> Conectividade:
        """Falta de energia vence Wi-Fi: sem rede eletrica o roteador tambem cai (premissa documentada)."""
        if self.janela_energia_em(t) is not None:
            return Conectividade.MAINS_DOWN
        if self.janela_wifi_em(t) is not None:
            return Conectividade.WIFI_DOWN
        return Conectividade.ONLINE

    def fim(self) -> datetime | None:
        """Fim da ultima janela (para saber ate quando drenar o buffer)."""
        fins = [j.fim for j in (*self.janelas_wifi, *self.janelas_energia)]
        return max(fins) if fins else None
