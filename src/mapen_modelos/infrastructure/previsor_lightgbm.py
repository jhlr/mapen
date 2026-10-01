"""Previsor LightGBM por equipamento, so com features de defasagem >= 24 h (sem lag 1)."""

from __future__ import annotations

import pandas as pd

from mapen_modelos.domain.features import ALVO
from mapen_modelos.domain.previsao import FEATURES_PREVISAO, montar_features_previsao
from mapen_modelos.infrastructure.lightgbm_modelo import ModeloLightGBM, TreinadorLightGBM


class PrevisorLightGBM:
    """Adaptador das portas `Previsor` e `PrevisorExplicavel`. Hiperparametros: os do `TreinadorLightGBM`."""

    nome = "lightgbm_lag24"
    features: tuple[str, ...] = FEATURES_PREVISAO

    def __init__(self, semente: int = 0, n_arvores: int = 300) -> None:
        self._treinador = TreinadorLightGBM(semente, n_arvores)

    def _ajustar(self, serie: pd.Series, treino_fim: pd.Timestamp) -> tuple[ModeloLightGBM, pd.DataFrame]:
        quadro = montar_features_previsao(
            serie, pd.Timestamp(serie.index[0]), pd.Timestamp(serie.index[-1]) + pd.Timedelta("1h")
        )
        treino = quadro[(quadro.index < treino_fim) & quadro[ALVO].notna()]
        return self._treinador.treinar_lightgbm(treino[list(self.features)], treino[ALVO]), quadro

    def prever(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.Series:
        modelo, quadro = self._ajustar(serie, treino_fim)
        x = quadro.reindex(alvo)[list(self.features)]
        return pd.Series(modelo.prever(x), index=alvo)

    def contribuicoes(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.DataFrame:
        modelo, quadro = self._ajustar(serie, treino_fim)
        x = quadro.reindex(alvo)[list(self.features)]
        return pd.DataFrame(modelo.contribuicoes(x), index=alvo, columns=list(self.features))

