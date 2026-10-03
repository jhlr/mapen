from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.explica import checar_d7, top_features
from mapen_modelos.domain.features import FEATURES
from mapen_modelos.domain.injecao import (
    ELEVACAO,
    LIGADO,
    PICO,
    equipamento_com_carga,
    injetar_anomalias,
    zona_contaminada,
)


def test_top_features_ordena_por_valor_absoluto() -> None:
    nomes = ("a", "b", "c", "d")
    top = top_features(np.array([0.1, -0.9, 0.4, 0.0]), nomes, 3)
    assert [c.feature for c in top] == ["b", "c", "a"]
    assert top[0].shap == -0.9


def test_d7_participacoes_somam_um_e_avisa_feature_dominante() -> None:
    shap = np.zeros((10, len(FEATURES)))
    shap[:, FEATURES.index("kw_lag1")] = 3.0
    shap[:, FEATURES.index("hora")] = 1.0
    c = checar_d7(shap, FEATURES)
    assert c.participacao_calendario == pytest.approx(0.25)
    assert c.participacao_historico == pytest.approx(0.75)
    assert sum(c.participacao_por_feature.values()) == pytest.approx(1.0)
    assert c.feature_dominante == "kw_lag1"
    assert c.avisos


def test_d7_sem_aviso_quando_nenhuma_feature_passa_de_metade() -> None:
    shap = np.ones((5, len(FEATURES)))
    c = checar_d7(shap, FEATURES)
    assert c.feature_dominante is None and not c.avisos
    assert c.participacao_calendario == pytest.approx(3 / len(FEATURES))


def test_d7_aponta_identidade_de_calendario_dominante() -> None:
    shap = np.zeros((5, len(FEATURES)))
    shap[:, FEATURES.index("hora")] = 2.0
    shap[:, FEATURES.index("kw_lag24")] = 1.0
    c = checar_d7(shap, FEATURES)
    assert c.feature_dominante == "hora"
    assert c.participacao_calendario == pytest.approx(2 / 3)


def _serie(horas: int = 24 * 14) -> pd.Series:
    idx = pd.date_range("2026-10-05", periods=horas, freq="1h")
    return pd.Series(1.0, index=idx)


def test_injecao_e_reprodutivel_e_nao_sobrepoe_eventos() -> None:
    a, ev_a = injetar_anomalias(_serie(), 4.0, np.random.default_rng(7), 2)
    b, ev_b = injetar_anomalias(_serie(), 4.0, np.random.default_rng(7), 2)
    assert a.equals(b) and ev_a == ev_b
    assert len(ev_a) == 6
    ordenados = sorted(ev_a, key=lambda e: e.inicio)
    assert all(x.fim < y.inicio for x, y in zip(ordenados, ordenados[1:], strict=False))


def test_injecao_altera_so_as_horas_dos_eventos_com_a_magnitude_esperada() -> None:
    base = _serie()
    nova, eventos = injetar_anomalias(base, 4.0, np.random.default_rng(3), 1)
    mudou = (nova != base).to_numpy()
    dentro = np.zeros(len(base), dtype=bool)
    for e in eventos:
        dentro |= np.asarray((base.index >= e.inicio) & (base.index < e.fim))
    assert (mudou <= dentro).all()
    pico = next(e for e in eventos if e.tipo == PICO)
    assert nova[pico.inicio] == pytest.approx(1.0 + 3 * 4.0)
    el = next(e for e in eventos if e.tipo == ELEVACAO)
    assert el.inicio.hour == 0 and (el.fim - el.inicio) == pd.Timedelta(hours=6)
    assert nova[el.inicio] == pytest.approx(1.0 + 0.5 * 4.0)
    lg = next(e for e in eventos if e.tipo == LIGADO)
    assert lg.inicio.hour == 20 and nova[lg.inicio] == pytest.approx(4.0)


def test_equipamento_sem_carga_nao_entra() -> None:
    idx = pd.date_range("2026-10-05", periods=48, freq="1h")
    assert not equipamento_com_carga(pd.Series(0.0, index=idx))
    assert equipamento_com_carga(pd.Series(1.0, index=idx))


def test_zona_contaminada_cobre_evento_janela_e_defasagens() -> None:
    base = _serie(24 * 10)
    _, eventos = injetar_anomalias(base, 4.0, np.random.default_rng(1), 1)
    pico = next(e for e in eventos if e.tipo == PICO)
    zona = zona_contaminada(pd.DatetimeIndex(base.index), [pico], (1, 24, 168), 24)
    p = int(np.flatnonzero(np.asarray(base.index == pico.inicio))[0])
    assert zona[p] and zona[p + 1] and zona[min(p + 24, len(zona) - 1)]
    assert zona.sum() <= 1 + 24 + 2
