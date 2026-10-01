"""Caso de uso DetectarAnomalias: alertas de z-score sazonal e de LightGBM, com explicacao."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from mapen_modelos.application.portas import Explicador, LeitorSeries
from mapen_modelos.application.treinar_e_avaliar import ResultadoTreino
from mapen_modelos.domain.anomalia import LIMIAR_Z_PADRAO, decidir_anomalia
from mapen_modelos.domain.baseline import esperado_em, zscore
from mapen_modelos.domain.explica import ChecagemD7, ContribuicaoFeature, checar_d7, top_features
from mapen_modelos.domain.features import ALVO, DEFASAGENS, FEATURES, montar_features

TIPO_ZSCORE = "zscore"
TIPO_LIGHTGBM = "lightgbm"
STATUS_CANDIDATO = "candidato_nao_corroborado"
AQUECIMENTO = pd.Timedelta(hours=max(DEFASAGENS))


@dataclass(frozen=True)
class Alerta:
    equipamento: str
    ts: pd.Timestamp
    tipo: str
    esperado: float
    observado: float
    z: float
    janela_inicio: pd.Timestamp
    janela_fim: pd.Timestamp
    baseline_fraca: bool
    top_shap: list[ContribuicaoFeature] | None = None


@dataclass
class ResultadoDeteccao:
    inicio: pd.Timestamp
    fim: pd.Timestamp
    limiar: float
    alertas: list[Alerta] = field(default_factory=list)
    d7_por_equipamento: dict[str, ChecagemD7] = field(default_factory=dict)
    d7_agregado: ChecagemD7 | None = None
    horas_avaliadas: int = 0


class DetectarAnomalias:
    def __init__(self, leitor: LeitorSeries, explicador: Explicador) -> None:
        self._leitor = leitor
        self._explicador = explicador

    def executar(
        self,
        sensor_id: str,
        treino: ResultadoTreino,
        inicio: pd.Timestamp,
        fim: pd.Timestamp,
        limiar: float = LIMIAR_Z_PADRAO,
    ) -> ResultadoDeteccao:
        """Le [inicio - aquecimento, fim) (o aquecimento so alimenta lags) e detecta em [inicio, fim)."""
        series = self._leitor.ler_series_horarias(sensor_id, inicio - AQUECIMENTO, fim)
        return self.detectar_em(series, treino, inicio, fim, limiar, explicar=True)

    def detectar_em(
        self,
        series: pd.DataFrame,
        treino: ResultadoTreino,
        inicio: pd.Timestamp,
        fim: pd.Timestamp,
        limiar: float,
        explicar: bool,
    ) -> ResultadoDeteccao:
        """Detecta sobre series ja carregadas (com aquecimento antes de `inicio`)."""
        resultado = ResultadoDeteccao(inicio, fim, limiar)
        todo_shap: list[np.ndarray] = []
        for equipamento, modelo in treino.modelos.items():
            serie = series[equipamento]
            quadro = montar_features(serie, pd.Timestamp(series.index.min()), fim)
            janela = quadro[quadro.index >= inicio]
            observado = janela[ALVO]
            base = modelo.baseline
            z_base = zscore(base, observado)
            flag_base = decidir_anomalia(z_base.to_numpy(), limiar)
            esperado_base = esperado_em(base, pd.DatetimeIndex(janela.index))
            for i in np.flatnonzero(flag_base).tolist():
                resultado.alertas.append(
                    Alerta(
                        equipamento, pd.Timestamp(janela.index[i]), TIPO_ZSCORE, float(esperado_base[i]),
                        float(observado.iloc[i]), float(z_base.iloc[i]), base.janela_inicio, base.janela_fim,
                        base.fraca,
                    )
                )
            x = janela[list(FEATURES)]
            previsto = modelo.regressor.prever(x)
            z_mod = (observado.to_numpy(dtype=np.float64) - previsto) / modelo.sigma_residuo
            flag_mod = decidir_anomalia(z_mod, limiar)
            resultado.horas_avaliadas += int(observado.notna().sum())
            shap_valido = np.empty((0, len(FEATURES)))
            posicao_valida = np.empty(0, dtype=np.int64)
            if explicar:
                valido = observado.notna().to_numpy()
                shap_valido = self._explicador.valores(modelo.regressor, x[valido])
                resultado.d7_por_equipamento[equipamento] = checar_d7(shap_valido, FEATURES)
                todo_shap.append(shap_valido)
                posicao_valida = np.flatnonzero(valido)
            for i in np.flatnonzero(flag_mod).tolist():
                top: list[ContribuicaoFeature] | None = None
                if explicar:
                    k = int(np.searchsorted(posicao_valida, i))
                    top = top_features(shap_valido[k], FEATURES, 3)
                resultado.alertas.append(
                    Alerta(
                        equipamento, pd.Timestamp(janela.index[i]), TIPO_LIGHTGBM, float(previsto[i]),
                        float(observado.iloc[i]), float(z_mod[i]), base.janela_inicio, base.janela_fim,
                        base.fraca, top,
                    )
                )
        if explicar and todo_shap:
            resultado.d7_agregado = checar_d7(np.vstack(todo_shap), FEATURES)
        resultado.alertas.sort(key=lambda a: (a.equipamento, a.ts, a.tipo))
        return resultado
