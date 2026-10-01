"""Previsores de referencia (sem aprendizado): seasonal-naive e o baseline sazonal existente."""

from __future__ import annotations

import numpy as np
import pandas as pd

from mapen_modelos.domain.baseline import ajustar_baseline, esperado_em
from mapen_modelos.domain.previsao import naive_sazonal


class PrevisorNaiveSazonal:
    """Adaptador da porta `Previsor`: repete o valor de `periodo_h` horas antes (24 ou 168)."""

    def __init__(self, periodo_h: int) -> None:
        self._periodo_h = periodo_h

    @property
    def nome(self) -> str:
        return f"seasonal_naive_{self._periodo_h}"

    def prever(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.Series:
        return pd.Series(naive_sazonal(serie, self._periodo_h, alvo), index=alvo)


class PrevisorBaselineSazonal:
    """Adaptador da porta `Previsor`: media por hora da semana na janela de treino (feriado = domingo)."""

    nome = "baseline_sazonal"

    def prever(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.Series:
        baseline = ajustar_baseline(serie[serie.index < treino_fim])
        return pd.Series(np.asarray(esperado_em(baseline, alvo)), index=alvo)
