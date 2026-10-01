"""Caso de uso CompararAntesDepois: economia normalizada pelo baseline, com validacao sintetica.

Nao existe intervencao real nos dados publicos. `reducao` aplica uma queda SINTETICA conhecida
no periodo "depois" para checar se o metodo a recupera: isso valida o METODO, nao uma economia.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from mapen_modelos.application.portas import LeitorSeries
from mapen_modelos.application.treinar_e_avaliar import ResultadoTreino
from mapen_modelos.domain.baseline import esperado_em
from mapen_modelos.domain.comparacao import ResultadoComparacao, aplicar_reducao, comparar_antes_depois

TOLERANCIA_PP_PADRAO = 3.0


@dataclass(frozen=True)
class ReducaoSintetica:
    equipamento: str
    fracao: float
    a_partir_de: pd.Timestamp


@dataclass
class ResultadoAntesDepois:
    inicio_antes: pd.Timestamp
    fim_antes: pd.Timestamp
    fim_depois: pd.Timestamp
    por_equipamento: dict[str, ResultadoComparacao] = field(default_factory=dict)
    reducao: ReducaoSintetica | None = None
    tolerancia_pp: float = TOLERANCIA_PP_PADRAO

    @property
    def recuperado_pct(self) -> float:
        if self.reducao is None:
            return float("nan")
        return self.por_equipamento[self.reducao.equipamento].economia_pct

    @property
    def dentro_da_tolerancia(self) -> bool:
        if self.reducao is None:
            return False
        return abs(self.recuperado_pct - 100.0 * self.reducao.fracao) <= self.tolerancia_pp


class CompararAntesDepois:
    def __init__(self, leitor: LeitorSeries) -> None:
        self._leitor = leitor

    def executar(
        self,
        sensor_id: str,
        treino: ResultadoTreino,
        inicio_antes: pd.Timestamp,
        fim_antes: pd.Timestamp,
        fim_depois: pd.Timestamp,
        reducao: ReducaoSintetica | None = None,
        tolerancia_pp: float = TOLERANCIA_PP_PADRAO,
    ) -> ResultadoAntesDepois:
        """Periodo antes = [inicio_antes, fim_antes), depois = [fim_antes, fim_depois)."""
        series = self._leitor.ler_series_horarias(sensor_id, inicio_antes, fim_depois)
        resultado = ResultadoAntesDepois(inicio_antes, fim_antes, fim_depois, {}, reducao, tolerancia_pp)
        for eq, modelo in treino.modelos.items():
            serie = series[eq]
            if reducao is not None and reducao.equipamento == eq:
                serie = aplicar_reducao(serie, reducao.a_partir_de, reducao.fracao)
            antes = serie[serie.index < fim_antes]
            depois = serie[serie.index >= fim_antes]
            esp_antes = pd.Series(esperado_em(modelo.baseline, pd.DatetimeIndex(antes.index)), index=antes.index)
            esp_depois = pd.Series(esperado_em(modelo.baseline, pd.DatetimeIndex(depois.index)), index=depois.index)
            resultado.por_equipamento[eq] = comparar_antes_depois(
                antes, esp_antes, depois, esp_depois, modelo.baseline.fraca
            )
        return resultado

    def varredura_reducao(
        self,
        sensor_id: str,
        treino: ResultadoTreino,
        inicio_antes: pd.Timestamp,
        fim_antes: pd.Timestamp,
        fim_depois: pd.Timestamp,
        fracao: float,
    ) -> dict[str, float]:
        """Recuperado (%) de uma reducao sintetica de `fracao` aplicada, uma de cada vez, a cada equipamento."""
        recuperado: dict[str, float] = {}
        for eq in treino.modelos:
            r = self.executar(
                sensor_id, treino, inicio_antes, fim_antes, fim_depois, ReducaoSintetica(eq, fracao, fim_antes)
            )
            recuperado[eq] = r.recuperado_pct
        return recuperado
