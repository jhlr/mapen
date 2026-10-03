from __future__ import annotations

import numpy as np
import pandas as pd

from mapen_modelos.domain.features import FEATURES, eh_feriado, montar_features, tipo_dia

T0 = pd.Timestamp("2026-10-05 00:00")  # segunda-feira


def _serie(horas: int, ausentes: tuple[int, ...] = ()) -> pd.Series:
    """kW = indice da hora (0, 1, 2, ...), exceto as horas ausentes (removidas do indice)."""
    idx = [T0 + pd.Timedelta(hours=h) for h in range(horas) if h not in ausentes]
    return pd.Series([float(h) for h in range(horas) if h not in ausentes], index=pd.DatetimeIndex(idx))


def test_features_calendario_e_lags_em_serie_completa() -> None:
    q = montar_features(_serie(400), T0, T0 + pd.Timedelta(hours=400))
    assert list(q.columns) == ["kw", *FEATURES]
    t = T0 + pd.Timedelta(hours=200)
    assert q.loc[t, "kw_lag1"] == 199.0
    assert q.loc[t, "kw_lag24"] == 176.0
    assert q.loc[t, "kw_lag168"] == 32.0
    assert q.loc[t, "hora"] == 8
    assert q.loc[t, "dia_semana"] == (T0 + pd.Timedelta(hours=200)).dayofweek


def test_janela_movel_usa_so_o_passado() -> None:
    q = montar_features(_serie(100), T0, T0 + pd.Timedelta(hours=100))
    t = T0 + pd.Timedelta(hours=50)
    esperado = np.mean(np.arange(26, 50))  # horas 26..49, sem a hora 50
    assert q.loc[t, "kw_media24"] == esperado
    assert pd.isna(q.loc[T0 + pd.Timedelta(hours=23), "kw_media24"])  # historico incompleto


def h(n: int) -> pd.Timestamp:
    return T0 + pd.Timedelta(hours=n)


def test_lacuna_nao_produz_lag_silenciosamente_errado() -> None:
    """Hora 100 ausente: ela vira NaN no calendario e nenhum lag/janela que a referencia inventa valor."""
    q = montar_features(_serie(400, ausentes=(100,)), T0, T0 + pd.Timedelta(hours=400))
    assert pd.isna(q.loc[h(100), "kw"])
    assert pd.isna(q.loc[h(101), "kw_lag1"])
    assert pd.isna(q.loc[h(124), "kw_lag24"])
    assert pd.isna(q.loc[h(268), "kw_lag168"])
    # pontos vizinhos nao afetados e correspondem ao ponto certo do calendario
    assert q.loc[h(102), "kw_lag1"] == 101.0
    assert q.loc[h(125), "kw_lag24"] == 101.0
    # janela de 24 h que inclui a hora ausente e NaN (sem min_periods frouxo)
    assert pd.isna(q.loc[h(110), "kw_media24"])
    assert not pd.isna(q.loc[h(125), "kw_media24"])


def test_feriado_vale_como_domingo() -> None:
    idx = pd.date_range("2026-09-06", periods=72, freq="1h")  # dom 6, seg 7 (feriado), ter 8
    assert eh_feriado(idx)[24:48].all()
    assert not eh_feriado(idx)[48:].any()
    assert set(tipo_dia(idx)[24:48]) == {6}
    assert set(tipo_dia(idx)[48:]) == {1}
