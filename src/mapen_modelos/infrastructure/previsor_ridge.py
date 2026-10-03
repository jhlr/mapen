"""Previsor Ridge: calendario one-hot, lags 24/48/168 e janela movel (defasagem >= 24 h).

O alpha sai de uma validacao cruzada temporal (`TimeSeriesSplit`) feita so com linhas de
treino, em cada ajuste. Linha com feature ausente nao e prevista (NaN): nada e imputado.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from mapen_modelos.domain.features import ALVO
from mapen_modelos.domain.previsao import (
    DEFASAGEM_MINIMA_H,
    FEATURES_JANELA_PREVISAO,
    FEATURES_LAGS_PREVISAO,
    FEATURES_PREVISAO,
    montar_features_previsao,
)

ALPHAS: tuple[float, ...] = (0.1, 1.0, 10.0, 100.0)
CATEGORICAS: tuple[str, ...] = ("hora", "dia_semana", "hora_semana")
NUMERICAS: tuple[str, ...] = ("feriado", *FEATURES_LAGS_PREVISAO, *FEATURES_JANELA_PREVISAO)
PARTICOES = 5


class PrevisorRidge:
    """Adaptador da porta `Previsor`."""

    nome = "ridge"
    features: tuple[str, ...] = FEATURES_PREVISAO

    def __init__(self, alphas: tuple[float, ...] = ALPHAS, particoes: int = PARTICOES) -> None:
        self._alphas = alphas
        self._particoes = particoes

    def prever(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.Series:
        quadro = montar_features_previsao(serie, pd.Timestamp(serie.index[0]), pd.Timestamp(serie.index[-1]) + pd.Timedelta("1h"))
        treino = quadro[quadro.index < treino_fim]
        treino = treino.dropna()
        modelo = self._modelo()
        modelo.fit(treino[list(self.features)], treino[ALVO])
        x = quadro.reindex(alvo)[list(self.features)]
        previsto = np.full(len(alvo), np.nan)
        completo = ~x.isna().any(axis=1).to_numpy()
        if completo.any():
            previsto[completo] = modelo.predict(x[completo])
        return pd.Series(previsto, index=alvo)

    def _modelo(self) -> Pipeline:
        pre = ColumnTransformer(
            [
                ("cal", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(CATEGORICAS)),
                ("num", StandardScaler(), list(NUMERICAS)),
            ]
        )
        cv = TimeSeriesSplit(n_splits=self._particoes, gap=DEFASAGEM_MINIMA_H)
        return Pipeline(
            [("pre", pre), ("ridge", RidgeCV(alphas=list(self._alphas), cv=cv, scoring="neg_mean_absolute_error"))]
        )
