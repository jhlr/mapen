from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from mapen_aconselhamento.ingest import defasar, reindexar

FREQ = "1h"
T0 = pd.Timestamp("2026-10-05 00:00")


def _serie_com_lacuna() -> pd.Series[float]:
    """Pontos em t0,t1,t4,t5; t2 e t3 (2 consecutivos) faltam."""
    idx = pd.DatetimeIndex([T0 + pd.Timedelta(hours=h) for h in (0, 1, 4, 5)])
    return pd.Series([1.0, 2.0, 5.0, 6.0], index=idx)


def _defasar_posicional(serie: pd.Series[float], periodos: int, freq: str) -> pd.Series[float]:
    """Referencia ingenua: shift posicional, pula a lacuna (o bug que o teste deve pegar)."""
    return serie.shift(periodos)


def _lacuna_nao_pulada(impl: Callable[[pd.Series[float], int, str], pd.Series[float]]) -> None:
    resultado = impl(_serie_com_lacuna(), 1, FREQ)
    t3 = T0 + pd.Timedelta(hours=3)
    t4 = T0 + pd.Timedelta(hours=4)
    t5 = T0 + pd.Timedelta(hours=5)
    # t4: o ponto anterior (t3) falta, logo o lag de t4 e NaN; nao pode herdar t1 (=2.0).
    assert t3 in resultado.index
    assert np.isnan(resultado[t4])
    assert resultado[t5] == pytest.approx(5.0)


def test_reindexar_marca_lacuna_sem_interpolar() -> None:
    dados = _serie_com_lacuna().to_frame("p")
    completo = reindexar(dados, FREQ)
    assert len(completo) == 6
    ausente = completo["p"].isna()
    assert list(ausente) == [False, False, True, True, False, False]
    assert completo["p"].notna().sum() == 4  # nenhum valor inventado


def test_lag_nao_pula_lacuna() -> None:
    _lacuna_nao_pulada(defasar)


@pytest.mark.xfail(strict=True, reason="referencia posicional ingenua: deve falhar (guard vermelho)")
def test_referencia_posicional_falha_no_teste_da_lacuna() -> None:
    _lacuna_nao_pulada(_defasar_posicional)
