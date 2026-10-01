"""Relogio (RTC) do dispositivo: segue o tempo real com uma deriva constante em ppm."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mapen_plataforma.domain.tempo import exigir_fuso


@dataclass(frozen=True)
class RelogioDispositivo:
    """`ler(real)` = real + (real - origem) * deriva_ppm / 1e6. Deriva positiva: o RTC adianta."""

    origem: datetime
    deriva_ppm: float = 0.0

    def __post_init__(self) -> None:
        exigir_fuso(self.origem, "origem")

    def ler(self, real: datetime) -> datetime:
        return real + (real - self.origem) * (self.deriva_ppm / 1_000_000.0)
