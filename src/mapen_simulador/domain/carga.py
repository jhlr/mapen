"""Perfil de carga que alimenta o gerador de amostras do dispositivo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_plataforma.domain.tempo import exigir_fuso
from mapen_simulador.domain.erros import ErroSimulador


@dataclass(frozen=True)
class Medida:
    """O que o sensor mede num instante: potencia de um equipamento."""

    equipamento: str
    potencia_w: float


@dataclass(frozen=True)
class SerieCarga:
    """Serie regular de potencia (W) de um equipamento; `None` = o sensor nao mediu (nao se inventa valor)."""

    equipamento: str
    inicio: datetime
    passo: timedelta
    valores_w: tuple[float | None, ...]

    def __post_init__(self) -> None:
        exigir_fuso(self.inicio, "inicio")
        if self.passo <= timedelta(0):
            raise ErroSimulador("passo da serie deve ser positivo")

    @property
    def fim(self) -> datetime:
        return self.inicio + self.passo * len(self.valores_w)

    def medidas_em(self, k: int) -> list[Medida]:
        if k < 0 or k >= len(self.valores_w) or self.valores_w[k] is None:
            return []
        valor = self.valores_w[k]
        assert valor is not None
        return [Medida(self.equipamento, valor)]

    def reiniciada_em(self, novo_inicio: datetime) -> SerieCarga:
        """Mesmos valores, outro eixo de tempo (para repetir uma serie historica no presente)."""
        return SerieCarga(self.equipamento, novo_inicio, self.passo, self.valores_w)
