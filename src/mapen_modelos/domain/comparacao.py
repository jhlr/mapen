"""Antes x depois com baseline normalizado.

O esperado vem de um baseline ajustado ANTES do periodo "antes" (hora da semana e feriado ja
normalizam o calendario). A deriva de nivel entre treino e o periodo "antes" e absorvida por
um fator `sum(obs_antes) / sum(esp_antes)`. O contrafactual do "depois" e esperado_depois x
fator; economia = contrafactual - observado, so nas horas com observado e esperado validos.
Temperatura nao entra (limite documentado).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ResultadoComparacao:
    kwh_antes: float
    kwh_depois: float
    fator_nivel: float
    kwh_contrafactual: float
    economia_kwh: float
    economia_pct: float
    horas_antes: int
    horas_depois: int
    baseline_fraca: bool


def comparar_antes_depois(
    observado_antes: pd.Series,
    esperado_antes: pd.Series,
    observado_depois: pd.Series,
    esperado_depois: pd.Series,
    baseline_fraca: bool,
) -> ResultadoComparacao:
    """Economia normalizada. As series devem estar alinhadas (mesmo indice) em cada periodo."""
    if not observado_antes.index.equals(esperado_antes.index):
        raise ValueError("antes: observado e esperado precisam do mesmo indice")
    if not observado_depois.index.equals(esperado_depois.index):
        raise ValueError("depois: observado e esperado precisam do mesmo indice")
    ok_a = observado_antes.notna() & esperado_antes.notna()
    ok_d = observado_depois.notna() & esperado_depois.notna()
    obs_a = float(observado_antes[ok_a].sum())
    esp_a = float(esperado_antes[ok_a].sum())
    obs_d = float(observado_depois[ok_d].sum())
    esp_d = float(esperado_depois[ok_d].sum())
    if esp_a <= 0.0 or esp_d <= 0.0:
        return ResultadoComparacao(
            obs_a, obs_d, float("nan"), float("nan"), float("nan"), float("nan"),
            int(ok_a.sum()), int(ok_d.sum()), baseline_fraca,
        )
    fator = obs_a / esp_a
    contrafactual = esp_d * fator
    economia = contrafactual - obs_d
    pct = float(100.0 * economia / contrafactual) if contrafactual > 0 else float("nan")
    return ResultadoComparacao(
        kwh_antes=obs_a,
        kwh_depois=obs_d,
        fator_nivel=fator,
        kwh_contrafactual=contrafactual,
        economia_kwh=economia,
        economia_pct=pct,
        horas_antes=int(ok_a.sum()),
        horas_depois=int(ok_d.sum()),
        baseline_fraca=baseline_fraca,
    )


def aplicar_reducao(serie: pd.Series, a_partir_de: pd.Timestamp, fracao: float) -> pd.Series:
    """Reducao sintetica: multiplica por (1 - fracao) de `a_partir_de` em diante."""
    if not 0.0 <= fracao < 1.0:
        raise ValueError("fracao deve estar em [0, 1)")
    fator = np.where(pd.DatetimeIndex(serie.index) >= a_partir_de, 1.0 - fracao, 1.0)
    return serie * fator
