from __future__ import annotations

import pandas as pd
import pytest

from mapen_aconselhamento.tarifa import BRANCA, CONVENCIONAL, Tarifas


@pytest.fixture(scope="module")
def tarifas() -> Tarifas:
    return Tarifas.carregar()


def test_convencional_preco_unico(tarifas: Tarifas) -> None:
    for ts in ("2026-10-05 03:00", "2026-10-05 19:00", "2026-10-10 12:00"):
        assert tarifas.preco_em(pd.Timestamp(ts), CONVENCIONAL) == pytest.approx(0.79886)


@pytest.mark.parametrize(
    ("ts", "esperado"),
    [
        ("2026-10-05 15:59", 0.66447),  # segunda, fora de ponta
        ("2026-10-05 16:00", 1.05341),  # intermediario
        ("2026-10-05 17:59", 1.05341),
        ("2026-10-05 18:00", 1.62479),  # ponta
        ("2026-10-05 20:59", 1.62479),
        ("2026-10-05 21:00", 0.66447),  # fora de ponta
        ("2026-10-05 00:00", 0.66447),
    ],
)
def test_branca_preco_por_horario(tarifas: Tarifas, ts: str, esperado: float) -> None:
    assert tarifas.preco_em(pd.Timestamp(ts), BRANCA) == pytest.approx(esperado)


def test_branca_fim_de_semana_sempre_fora_de_ponta(tarifas: Tarifas) -> None:
    sabado_ponta = pd.Timestamp("2026-10-03 19:00")
    domingo_interm = pd.Timestamp("2026-10-04 17:00")
    assert tarifas.preco_em(sabado_ponta, BRANCA) == pytest.approx(0.66447)
    assert tarifas.preco_em(domingo_interm, BRANCA) == pytest.approx(0.66447)
