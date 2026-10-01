"""Cenario de falhas em arquivo JSON, com deslocamentos em minutos a partir do inicio da simulacao.

    {"bateria_min": 15, "deriva_ppm": 0, "wifi": [{"inicio_min": 10, "duracao_min": 10}],
     "energia": [{"inicio_min": 60, "duracao_min": 30}]}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from mapen_simulador.domain.cenario import Cenario, Janela
from mapen_simulador.domain.erros import ErroSimulador


@dataclass(frozen=True)
class CenarioRelativo:
    """Janelas em minutos desde o inicio; vira `Cenario` quando o inicio e conhecido."""

    wifi: tuple[tuple[float, float], ...] = ()
    energia: tuple[tuple[float, float], ...] = ()
    bateria_min: float = 0.0
    deriva_ppm: float = 0.0

    def a_partir_de(self, inicio: datetime) -> Cenario:
        def janelas(itens: tuple[tuple[float, float], ...]) -> tuple[Janela, ...]:
            return tuple(
                Janela(inicio + timedelta(minutes=ini), inicio + timedelta(minutes=ini + dur)) for ini, dur in itens
            )

        return Cenario(janelas(self.wifi), janelas(self.energia), timedelta(minutes=self.bateria_min))


def _janelas(bruto: object) -> tuple[tuple[float, float], ...]:
    if not isinstance(bruto, list):
        raise ErroSimulador("janelas devem ser uma lista")
    saida: list[tuple[float, float]] = []
    for item in bruto:
        if not isinstance(item, dict):
            raise ErroSimulador("cada janela deve ser um objeto com inicio_min e duracao_min")
        saida.append((float(item["inicio_min"]), float(item["duracao_min"])))
    return tuple(saida)


def ler_cenario(caminho: Path) -> CenarioRelativo:
    dados = json.loads(caminho.read_text())
    if not isinstance(dados, dict):
        raise ErroSimulador("o arquivo de cenario deve ser um objeto JSON")
    return CenarioRelativo(
        wifi=_janelas(dados.get("wifi", [])),
        energia=_janelas(dados.get("energia", [])),
        bateria_min=float(dados.get("bateria_min", 0.0)),
        deriva_ppm=float(dados.get("deriva_ppm", 0.0)),
    )
