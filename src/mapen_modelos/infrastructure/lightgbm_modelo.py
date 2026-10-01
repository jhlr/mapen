"""Regressor LightGBM por equipamento (um modelo por serie: identidade nao e feature)."""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from mapen_modelos.application.portas import Regressor


class ModeloLightGBM:
    """Adaptador da porta `Regressor`; guarda o booster para as contribuicoes TreeSHAP."""

    def __init__(self, modelo: lgb.LGBMRegressor) -> None:
        self._modelo = modelo

    def prever(self, x: pd.DataFrame) -> np.ndarray:
        return np.asarray(self._modelo.predict(x), dtype=np.float64)

    def contribuicoes(self, x: pd.DataFrame) -> np.ndarray:
        """Contribuicao TreeSHAP exata por feature (sem a coluna do valor base)."""
        completo = np.asarray(self._modelo.predict(x, pred_contrib=True), dtype=np.float64)
        return completo[:, :-1]


class TreinadorLightGBM:
    """Adaptador da porta `TreinadorModelo` com parametros fixos e semente fixa."""

    def __init__(self, semente: int = 0, n_arvores: int = 300) -> None:
        self._semente = semente
        self._n_arvores = n_arvores

    def treinar(self, x: pd.DataFrame, y: pd.Series) -> Regressor:
        return self.treinar_lightgbm(x, y)

    def treinar_lightgbm(self, x: pd.DataFrame, y: pd.Series) -> ModeloLightGBM:
        modelo = lgb.LGBMRegressor(
            n_estimators=self._n_arvores,
            learning_rate=0.05,
            num_leaves=15,
            min_child_samples=20,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            random_state=self._semente,
            n_jobs=1,
            deterministic=True,
            force_row_wise=True,
            verbose=-1,
        )
        modelo.fit(x, y)
        return ModeloLightGBM(modelo)
