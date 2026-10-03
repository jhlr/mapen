"""Caso de uso TreinarEAvaliar: walk-forward por equipamento (baseline x LightGBM) e modelos finais."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from mapen_modelos.application.portas import LeitorSeries, Regressor, TreinadorModelo
from mapen_modelos.domain.baseline import (
    PISO_DESVIO_ABSOLUTO_KW,
    PISO_DESVIO_RELATIVO,
    BaselineSazonal,
    ajustar_baseline,
    esperado_em,
)
from mapen_modelos.domain.features import ALVO, FEATURES, montar_features
from mapen_modelos.domain.injecao import equipamento_com_carga
from mapen_modelos.domain.validacao import Dobra, dobras_walk_forward, verificar_sem_vazamento


@dataclass(frozen=True)
class ConfigAvaliacao:
    treino_inicial: pd.Timedelta = pd.Timedelta(weeks=8)
    teste: pd.Timedelta = pd.Timedelta(weeks=2)


@dataclass(frozen=True)
class MetricaDobra:
    dobra: int
    horas_teste: int
    mae_baseline: float
    mae_modelo: float


@dataclass(frozen=True)
class ModeloEquipamento:
    """Baseline e regressor finais (treinados em toda a janela) de um equipamento."""

    equipamento: str
    baseline: BaselineSazonal
    regressor: Regressor
    sigma_residuo: float  # desvio dos residuos fora da amostra das dobras (kW)


@dataclass(frozen=True)
class MetricaEquipamento:
    equipamento: str
    horas_teste: int
    mae_baseline: float
    mae_modelo: float
    por_dobra: list[MetricaDobra]


@dataclass
class ResultadoTreino:
    sensor_id: str
    inicio: pd.Timestamp
    fim: pd.Timestamp
    dobras: list[Dobra]
    modelos: dict[str, ModeloEquipamento] = field(default_factory=dict)
    metricas: dict[str, MetricaEquipamento] = field(default_factory=dict)
    sem_carga: list[str] = field(default_factory=list)
    horas_calendario: int = 0
    horas_validas: dict[str, int] = field(default_factory=dict)


def _mae(erro: np.ndarray) -> float:
    return float(np.abs(erro).mean()) if erro.size else float("nan")


class TreinarEAvaliar:
    """Dono do ciclo de treino: avalia por walk-forward e devolve os modelos finais."""

    def __init__(self, leitor: LeitorSeries, treinador: TreinadorModelo) -> None:
        self._leitor = leitor
        self._treinador = treinador

    def executar(
        self,
        sensor_id: str,
        inicio: pd.Timestamp,
        fim: pd.Timestamp,
        config: ConfigAvaliacao = ConfigAvaliacao(),
    ) -> ResultadoTreino:
        series = self._leitor.ler_series_horarias(sensor_id, inicio, fim)
        dobras = dobras_walk_forward(inicio, fim, config.treino_inicial, config.teste)
        if not dobras:
            raise ValueError("janela curta demais para uma dobra walk-forward")
        verificar_sem_vazamento(dobras)
        resultado = ResultadoTreino(sensor_id, inicio, fim, dobras, horas_calendario=len(series))
        for equipamento in series.columns:
            serie = series[equipamento]
            resultado.horas_validas[str(equipamento)] = int(serie.notna().sum())
            if not equipamento_com_carga(serie):
                resultado.sem_carga.append(str(equipamento))
                continue
            self._avaliar_equipamento(resultado, str(equipamento), serie, dobras)
        return resultado

    def _avaliar_equipamento(
        self, resultado: ResultadoTreino, equipamento: str, serie: pd.Series, dobras: list[Dobra]
    ) -> None:
        quadro = montar_features(serie, resultado.inicio, resultado.fim)
        por_dobra: list[MetricaDobra] = []
        erros_base: list[np.ndarray] = []
        erros_modelo: list[np.ndarray] = []
        for k, d in enumerate(dobras):
            treino = quadro[(quadro.index >= d.treino_inicio) & (quadro.index < d.treino_fim)]
            teste = quadro[(quadro.index >= d.teste_inicio) & (quadro.index < d.teste_fim)]
            teste = teste[teste[ALVO].notna()]
            baseline = ajustar_baseline(treino[ALVO])
            esperado = esperado_em(baseline, pd.DatetimeIndex(teste.index))
            e_base = teste[ALVO].to_numpy(dtype=np.float64) - esperado
            modelo = self._treinar(treino)
            e_mod = teste[ALVO].to_numpy(dtype=np.float64) - modelo.prever(teste[list(FEATURES)])
            erros_base.append(e_base)
            erros_modelo.append(e_mod)
            por_dobra.append(MetricaDobra(k, len(teste), _mae(e_base), _mae(e_mod)))
        todo_base = np.concatenate(erros_base)
        todo_mod = np.concatenate(erros_modelo)
        resultado.metricas[equipamento] = MetricaEquipamento(
            equipamento, int(todo_base.size), _mae(todo_base), _mae(todo_mod), por_dobra
        )
        media = float(quadro[ALVO].mean())
        piso = max(PISO_DESVIO_RELATIVO * abs(media), PISO_DESVIO_ABSOLUTO_KW)
        sigma = max(float(todo_mod.std(ddof=1)), piso)
        resultado.modelos[equipamento] = ModeloEquipamento(
            equipamento, ajustar_baseline(quadro[ALVO]), self._treinar(quadro), sigma
        )

    def _treinar(self, janela: pd.DataFrame) -> Regressor:
        valido = janela[janela[ALVO].notna()]
        return self._treinador.treinar(valido[list(FEATURES)], valido[ALVO])
