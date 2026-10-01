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
from mapen_modelos.domain.comparacao import (
    ResultadoComparacao,
    ResultadoComparacaoControle,
    aplicar_reducao,
    comparar_antes_depois,
    comparar_com_controle,
    selecionar_controles,
)

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
    por_equipamento_controle: dict[str, ResultadoComparacaoControle] = field(default_factory=dict)

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

    @property
    def recuperado_controle_pct(self) -> float:
        if self.reducao is None:
            return float("nan")
        return self.por_equipamento_controle[self.reducao.equipamento].economia_pct

    @property
    def dentro_da_tolerancia_controle(self) -> bool:
        if self.reducao is None:
            return False
        return abs(self.recuperado_controle_pct - 100.0 * self.reducao.fracao) <= self.tolerancia_pp


@dataclass(frozen=True)
class Varredura:
    """Recuperado (%) por equipamento tratado, nos dois metodos, e os controles usados pelo novo."""

    baseline_pct: dict[str, float]
    controle_pct: dict[str, float]
    controles: dict[str, tuple[str, ...]]


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
        inicio_pre: pd.Timestamp | None = None,
    ) -> ResultadoAntesDepois:
        """Periodo antes = [inicio_antes, fim_antes), depois = [fim_antes, fim_depois).

        `inicio_pre` (padrao `inicio_antes`) abre o pre-periodo usado so para escolher controles.
        Equipamentos com a reducao sintetica nunca entram como controle de outro.
        """
        inicio_leitura = inicio_pre if inicio_pre is not None else inicio_antes
        series = self._leitor.ler_series_horarias(sensor_id, inicio_leitura, fim_depois)
        resultado = ResultadoAntesDepois(inicio_antes, fim_antes, fim_depois, {}, reducao, tolerancia_pp)
        pool = {
            eq: series[eq] for eq in treino.modelos if reducao is None or reducao.equipamento != eq
        }
        pre = {eq: s[s.index < fim_antes] for eq, s in pool.items()}
        for eq, modelo in treino.modelos.items():
            serie = series[eq]
            if reducao is not None and reducao.equipamento == eq:
                serie = aplicar_reducao(serie, reducao.a_partir_de, reducao.fracao)
            antes = serie[(serie.index >= inicio_antes) & (serie.index < fim_antes)]
            depois = serie[serie.index >= fim_antes]
            esp_antes = pd.Series(esperado_em(modelo.baseline, pd.DatetimeIndex(antes.index)), index=antes.index)
            esp_depois = pd.Series(esperado_em(modelo.baseline, pd.DatetimeIndex(depois.index)), index=depois.index)
            resultado.por_equipamento[eq] = comparar_antes_depois(
                antes, esp_antes, depois, esp_depois, modelo.baseline.fraca
            )
            pre_alvo = {**pre, eq: series[eq][series[eq].index < fim_antes]}
            controles = selecionar_controles(eq, pre_alvo)
            resultado.por_equipamento_controle[eq] = comparar_com_controle(
                antes,
                depois,
                {c: pool[c][(pool[c].index >= inicio_antes) & (pool[c].index < fim_antes)] for c in controles},
                {c: pool[c][pool[c].index >= fim_antes] for c in controles},
                modelo.baseline.fraca,
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
        inicio_pre: pd.Timestamp | None = None,
    ) -> Varredura:
        """Recuperado (%) de uma reducao sintetica de `fracao` aplicada, uma de cada vez, a cada equipamento."""
        baseline: dict[str, float] = {}
        controle: dict[str, float] = {}
        usados: dict[str, tuple[str, ...]] = {}
        for eq in treino.modelos:
            r = self.executar(
                sensor_id, treino, inicio_antes, fim_antes, fim_depois,
                ReducaoSintetica(eq, fracao, fim_antes), inicio_pre=inicio_pre,
            )
            baseline[eq] = r.recuperado_pct
            controle[eq] = r.recuperado_controle_pct
            usados[eq] = r.por_equipamento_controle[eq].controles
        return Varredura(baseline, controle, usados)
