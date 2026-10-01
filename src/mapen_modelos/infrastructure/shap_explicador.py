"""Explicador de valores SHAP para modelos LightGBM.

Usa a contribuicao TreeSHAP nativa do LightGBM (`pred_contrib=True`), que e o mesmo algoritmo
do `shap.TreeExplainer`: conferido em 2026-10-01 com diferenca maxima 0.0 (valores e valor
base). O pacote `shap` nao e importado porque a importacao dele (0.52, com matplotlib atual)
emite `PendingDeprecationWarning` de codigo de terceiros, que quebra a suite com `-W error`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mapen_modelos.application.portas import Regressor
from mapen_modelos.infrastructure.lightgbm_modelo import ModeloLightGBM


class ExplicadorShap:
    """Adaptador da porta `Explicador`."""

    def valores(self, modelo: Regressor, x: pd.DataFrame) -> np.ndarray:
        if not isinstance(modelo, ModeloLightGBM):
            raise TypeError(f"ExplicadorShap so explica ModeloLightGBM, veio {type(modelo).__name__}")
        return modelo.contribuicoes(x)
