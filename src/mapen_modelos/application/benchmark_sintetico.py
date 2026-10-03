"""Caso de uso BenchmarkSintetico: injeta anomalias conhecidas num periodo e mede deteccao.

SINTETICO: nao ha rotulo real, entao taxa de deteccao e de falso alarme valem so para as
anomalias injetadas aqui. Nao e precisao/recall em dado real.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from mapen_modelos.application.detectar_anomalias import (
    AQUECIMENTO,
    TIPO_LIGHTGBM,
    TIPO_ZSCORE,
    DetectarAnomalias,
)
from mapen_modelos.application.injecao_periodo import injetar_no_periodo
from mapen_modelos.application.portas import LeitorSeries
from mapen_modelos.application.treinar_e_avaliar import ResultadoTreino
from mapen_modelos.domain.features import DEFASAGENS, JANELA_MOVEL
from mapen_modelos.domain.injecao import TIPOS, zona_contaminada


@dataclass
class TaxasDetector:
    injetados: dict[str, int] = field(default_factory=dict)
    detectados: dict[str, int] = field(default_factory=dict)
    alertas_fora: int = 0
    horas_fora: int = 0

    def taxa_deteccao(self, tipo: str | None = None) -> float:
        tipos = TIPOS if tipo is None else (tipo,)
        inj = sum(self.injetados.get(t, 0) for t in tipos)
        det = sum(self.detectados.get(t, 0) for t in tipos)
        return det / inj if inj else float("nan")

    def taxa_falso_alarme(self) -> float:
        return self.alertas_fora / self.horas_fora if self.horas_fora else float("nan")


@dataclass
class ResultadoBenchmark:
    sintetico: bool
    semente: int
    por_tipo: int
    limiar: float
    inicio: pd.Timestamp
    fim: pd.Timestamp
    equipamentos: list[str]
    taxas: dict[str, TaxasDetector]


class BenchmarkSintetico:
    def __init__(self, leitor: LeitorSeries, detector: DetectarAnomalias) -> None:
        self._leitor = leitor
        self._detector = detector

    def executar(
        self,
        sensor_id: str,
        treino: ResultadoTreino,
        inicio: pd.Timestamp,
        fim: pd.Timestamp,
        limiar: float,
        semente: int,
        por_tipo: int,
    ) -> ResultadoBenchmark:
        series = self._leitor.ler_series_horarias(sensor_id, treino.inicio, fim)
        taxas = {TIPO_ZSCORE: TaxasDetector(), TIPO_LIGHTGBM: TaxasDetector()}
        equipamentos = list(treino.modelos)
        # A injecao e a escala dos eventos (P95) saem so do aquecimento antes de `inicio`, como no
        # benchmark original; o historico completo do treino so alimenta a escala do z-score.
        recorte = series.loc[series.index >= inicio - AQUECIMENTO, equipamentos]
        injetada_recorte, eventos_por_eq = injetar_no_periodo(recorte, equipamentos, inicio, semente, por_tipo)
        injetada = series.copy()
        injetada.loc[injetada_recorte.index, equipamentos] = injetada_recorte
        resultado = self._detector.detectar_em(injetada, treino, inicio, fim, limiar, explicar=False)
        indice_det = pd.DatetimeIndex(series.index[series.index >= inicio])
        for eq in equipamentos:
            eventos = eventos_por_eq[eq]
            zona = zona_contaminada(indice_det, eventos, DEFASAGENS, JANELA_MOVEL)
            valido = injetada.loc[injetada.index >= inicio, eq].notna().to_numpy()
            for tipo_det, t in taxas.items():
                ts_alerta = [a.ts for a in resultado.alertas if a.equipamento == eq and a.tipo == tipo_det]
                for ev in eventos:
                    t.injetados[ev.tipo] = t.injetados.get(ev.tipo, 0) + 1
                    if any(ev.inicio <= ts < ev.fim for ts in ts_alerta):
                        t.detectados[ev.tipo] = t.detectados.get(ev.tipo, 0) + 1
                fora = ~zona & valido
                t.horas_fora += int(fora.sum())
                pos_alerta = set(indice_det.get_indexer(pd.DatetimeIndex(ts_alerta)).tolist())
                t.alertas_fora += sum(1 for p in pos_alerta if p >= 0 and fora[p])
        return ResultadoBenchmark(True, semente, por_tipo, limiar, inicio, fim, equipamentos, taxas)
