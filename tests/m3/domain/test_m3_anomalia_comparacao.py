from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.anomalia import decidir_anomalia
from mapen_modelos.domain.comparacao import aplicar_reducao, comparar_antes_depois

T0 = pd.Timestamp("2026-10-05")


def test_decidir_anomalia_nos_dois_sentidos_e_ignora_nan() -> None:
    z = np.array([0.0, 3.9, 4.0, -4.5, np.nan])
    assert decidir_anomalia(z, 4.0).tolist() == [False, False, True, True, False]


def test_limiar_invalido() -> None:
    with pytest.raises(ValueError):
        decidir_anomalia(np.array([1.0]), 0.0)


def _par(horas: int, valor: float, inicio: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    idx = pd.date_range(inicio, periods=horas, freq="1h")
    return pd.Series(valor, index=idx), pd.Series(valor, index=idx)


def test_comparacao_recupera_reducao_conhecida_com_deriva_de_nivel() -> None:
    """Consumo 20% abaixo do esperado ja no antes (deriva) e mais 15% no depois: recupera 15%."""
    idx_a = pd.date_range(T0, periods=168, freq="1h")
    idx_d = pd.date_range(T0 + pd.Timedelta(weeks=1), periods=168, freq="1h")
    esp_a, esp_d = pd.Series(5.0, index=idx_a), pd.Series(5.0, index=idx_d)
    obs_a = esp_a * 0.8
    obs_d = aplicar_reducao(esp_d * 0.8, idx_d[0], 0.15)
    r = comparar_antes_depois(obs_a, esp_a, obs_d, esp_d, baseline_fraca=False)
    assert r.fator_nivel == pytest.approx(0.8)
    assert r.economia_pct == pytest.approx(15.0)
    assert r.economia_kwh == pytest.approx(0.8 * 5.0 * 168 * 0.15)
    assert not r.baseline_fraca


def test_comparacao_ignora_horas_sem_dado_e_propaga_baseline_fraca() -> None:
    idx = pd.date_range(T0, periods=48, freq="1h")
    esp = pd.Series(2.0, index=idx)
    obs = pd.Series(2.0, index=idx)
    obs.iloc[5] = np.nan
    r = comparar_antes_depois(obs, esp, obs, esp, baseline_fraca=True)
    assert r.horas_antes == 47 and r.baseline_fraca
    assert r.economia_pct == pytest.approx(0.0)


def test_comparacao_exige_indices_alinhados() -> None:
    a, b = _par(10, 1.0, T0)
    c, d = _par(10, 1.0, T0 + pd.Timedelta(days=3))
    with pytest.raises(ValueError):
        comparar_antes_depois(a, d, c, d, False)


def test_aplicar_reducao_so_depois_da_data_e_valida_fracao() -> None:
    idx = pd.date_range(T0, periods=4, freq="1h")
    s = aplicar_reducao(pd.Series(10.0, index=idx), idx[2], 0.5)
    assert s.tolist() == [10.0, 10.0, 5.0, 5.0]
    with pytest.raises(ValueError):
        aplicar_reducao(s, idx[0], 1.0)
