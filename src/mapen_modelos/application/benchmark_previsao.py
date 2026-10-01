"""Benchmark SINTETICO com o residuo de um previsor do dia seguinte como sinal de anomalia.

Mesmas anomalias do benchmark sintetico original (mesma semente, mesmo gerador, mesma escala).
Detector: |observado - previsto| / sigma >= limiar, sigma = desvio do residuo fora da amostra
nas dobras walk-forward. Nao e precisao/recall em dado real: vale so para os eventos injetados.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mapen_modelos.application.benchmark_sintetico import TaxasDetector
from mapen_modelos.application.detectar_anomalias import AQUECIMENTO
from mapen_modelos.application.injecao_periodo import injetar_no_periodo
from mapen_modelos.application.portas import Previsor
from mapen_modelos.domain.anomalia import decidir_anomalia
from mapen_modelos.domain.injecao import zona_contaminada
from mapen_modelos.domain.previsao import DEFASAGENS_PREVISAO, DEFASAGEM_MINIMA_H, JANELA_PREVISAO

# Zona contaminada: as features de janela cobrem [t-47, t-24], logo um evento em p contamina
# t em [p+24, p+47]; usa-se janela de 2 x 24 h (conservador) mais as defasagens 24, 48 e 168.
JANELA_ZONA_H = JANELA_PREVISAO + DEFASAGEM_MINIMA_H


@dataclass
class ResultadoBenchmarkPrevisao:
    sintetico: bool
    previsor: str
    semente: int
    por_tipo: int
    limiar: float
    equipamentos: list[str]
    taxas: TaxasDetector


class BenchmarkPrevisao:
    def executar(
        self,
        series: pd.DataFrame,
        previsor: Previsor,
        sigma: dict[str, float],
        inicio: pd.Timestamp,
        fim: pd.Timestamp,
        limiar: float,
        semente: int,
        por_tipo: int,
    ) -> ResultadoBenchmarkPrevisao:
        """`series` cobre [inicio_total, fim); a injecao so toca [inicio, fim)."""
        equipamentos = list(sigma)
        recorte = series.loc[series.index >= inicio - AQUECIMENTO, equipamentos]
        injetada_recorte, eventos_por_eq = injetar_no_periodo(recorte, equipamentos, inicio, semente, por_tipo)
        injetada = series[equipamentos].copy()
        injetada.loc[injetada_recorte.index, equipamentos] = injetada_recorte
        alvo = pd.date_range(inicio, fim, freq="1h", inclusive="left")
        taxas = TaxasDetector()
        for eq in equipamentos:
            serie = injetada[eq]
            previsto = np.maximum(previsor.prever(serie, inicio, alvo).reindex(alvo).to_numpy(dtype=np.float64), 0.0)
            observado = serie.reindex(alvo).to_numpy(dtype=np.float64)
            z = (observado - previsto) / sigma[eq]
            flag = decidir_anomalia(z)
            eventos = eventos_por_eq[eq]
            zona = zona_contaminada(alvo, eventos, DEFASAGENS_PREVISAO, JANELA_ZONA_H)
            fora = ~zona & ~np.isnan(observado)
            ts_alerta = pd.DatetimeIndex(alvo[flag])
            for ev in eventos:
                taxas.injetados[ev.tipo] = taxas.injetados.get(ev.tipo, 0) + 1
                if bool(((ts_alerta >= ev.inicio) & (ts_alerta < ev.fim)).any()):
                    taxas.detectados[ev.tipo] = taxas.detectados.get(ev.tipo, 0) + 1
            taxas.horas_fora += int(fora.sum())
            taxas.alertas_fora += int((flag & fora).sum())
        return ResultadoBenchmarkPrevisao(True, previsor.nome, semente, por_tipo, limiar, equipamentos, taxas)
