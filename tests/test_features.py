from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_aconselhamento.features import adicionar_lags

FREQ = "1h"
T0 = pd.Timestamp("2026-10-05 00:00")


def _frame_com_lacuna() -> pd.DataFrame:
    """Pontos em t0,t1,t4,t5; t2 e t3 (2 consecutivos) faltam."""
    idx = pd.DatetimeIndex([T0 + pd.Timedelta(hours=h) for h in (0, 1, 4, 5)])
    return pd.DataFrame({"p": [1.0, 2.0, 5.0, 6.0]}, index=idx)


def _lag_posicional_ingenuo(dados: pd.DataFrame, n: int) -> pd.Series:
    """Referencia ruim: shift posicional sobre a serie com lacuna."""
    return dados["p"].shift(n)


def test_lag_nao_pula_a_lacuna() -> None:
    resultado = adicionar_lags(_frame_com_lacuna(), "p", [1, 3], FREQ)
    t4 = T0 + pd.Timedelta(hours=4)
    t5 = T0 + pd.Timedelta(hours=5)
    assert np.isnan(resultado.loc[t4, "p_lag1"])  # t3 ausente
    assert resultado.loc[t5, "p_lag1"] == 5.0


def test_lag3_aponta_ponto_correto() -> None:
    resultado = adicionar_lags(_frame_com_lacuna(), "p", [3], FREQ)
    t4 = T0 + pd.Timedelta(hours=4)
    assert resultado.loc[t4, "p_lag3"] == 2.0  # t1


def test_referencia_ingenua_falha_no_ponto_da_lacuna() -> None:
    """O shift posicional devolve valor onde o lag correto e NaN."""
    dados = _frame_com_lacuna()
    t4 = T0 + pd.Timedelta(hours=4)
    ingenuo = _lag_posicional_ingenuo(dados, 1)
    correto = adicionar_lags(dados, "p", [1], FREQ).loc[t4, "p_lag1"]
    assert not np.isnan(ingenuo.loc[t4])  # ingenuo inventa 2.0
    assert np.isnan(correto)


def test_defasagem_invalida() -> None:
    with pytest.raises(ValueError):
        adicionar_lags(_frame_com_lacuna(), "p", [0], FREQ)
