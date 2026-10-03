from __future__ import annotations

import pandas as pd
import pytest

from mapen_aconselhamento.domain.custo import custo_por_faixa, custo_total
from mapen_aconselhamento.domain.ranking import pct_ausente_por_equipamento, top_n
from mapen_aconselhamento.domain.tarifa import BRANCA, CONVENCIONAL, Tarifas
from mapen_aconselhamento.infrastructure.tarifa_csv import carregar_tarifas


def _fixture_24h() -> pd.DataFrame:
    """Segunda-feira, 24 h, um equipamento consumindo 2 kWh a cada hora (48 kWh)."""
    ts = pd.date_range("2026-10-05 00:00", periods=24, freq="1h")
    return pd.DataFrame({"ts": ts, "equipamento_id": "z1_AC1", "kwh": 2.0})


def test_custo_convencional_fixture_24h() -> None:
    # Manual: 48 kWh x 0,79886 = 38,34528
    custos = custo_por_faixa(_fixture_24h(), carregar_tarifas(), CONVENCIONAL)
    assert custo_total(custos) == pytest.approx(38.35, abs=0.01)


def test_custo_branca_fixture_24h() -> None:
    # Manual: ponta 3 h x 2 kWh x 1,62479 = 9,74874
    #         intermediario 2 h x 2 x 1,05341 = 4,21364
    #         fora de ponta 19 h x 2 x 0,66447 = 25,24986 -> total 39,21224
    custos = custo_por_faixa(_fixture_24h(), carregar_tarifas(), BRANCA)
    assert custo_total(custos) == pytest.approx(39.21, abs=0.01)
    por_faixa = custos.set_index("faixa")["kwh"]
    assert por_faixa["ponta"] == pytest.approx(6.0)
    assert por_faixa["intermediario"] == pytest.approx(4.0)
    assert por_faixa["fora_ponta"] == pytest.approx(38.0)


def test_pontos_ausentes_nao_entram_no_custo() -> None:
    leituras = _fixture_24h()
    leituras.loc[10:11, "kwh"] = float("nan")
    custos = custo_por_faixa(leituras, carregar_tarifas(), CONVENCIONAL)
    assert custo_total(custos) == pytest.approx(44 * 0.79886)


def test_top_n_ordena_por_custo() -> None:
    custos = pd.DataFrame(
        {
            "equipamento_id": ["a", "b", "c", "b"],
            "faixa": ["unico"] * 4,
            "kwh": [1.0, 5.0, 2.0, 1.0],
            "custo_rs": [1.0, 5.0, 2.0, 1.0],
        }
    )
    ausencia = pd.Series({"a": 0.0, "b": 12.5, "c": 0.0})
    top = top_n(custos, ausencia, 2)
    assert list(top["equipamento_id"]) == ["b", "c"]
    assert list(top["custo_rs"]) == [6.0, 2.0]
    assert list(top["pct_ausente"]) == [12.5, 0.0]


def test_pct_ausente_por_equipamento() -> None:
    leituras = pd.DataFrame(
        {"equipamento_id": ["a", "a", "a", "a", "b"], "ausente": [True, False, False, False, False]}
    )
    pct = pct_ausente_por_equipamento(leituras)
    assert pct["a"] == pytest.approx(25.0)
    assert pct["b"] == pytest.approx(0.0)
