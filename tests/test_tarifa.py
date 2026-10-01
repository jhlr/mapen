from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from mapen_aconselhamento.tarifa import BRANCA, CONVENCIONAL, Tarifas, feriados_nacionais

PONTA, INTERM, FORA = 1.62479, 1.05341, 0.66447


@pytest.fixture(scope="module")
def tarifas() -> Tarifas:
    return Tarifas.carregar()


def test_convencional_preco_unico(tarifas: Tarifas) -> None:
    for ts in ("2026-10-05 03:00", "2026-10-05 19:00", "2026-10-10 12:00"):
        assert tarifas.preco_em(pd.Timestamp(ts), CONVENCIONAL) == pytest.approx(0.79886)


@pytest.mark.parametrize(
    ("ts", "esperado"),
    [
        ("2026-10-05 00:00", FORA),
        ("2026-10-05 15:59", FORA),  # segunda, dia util
        ("2026-10-05 16:00", INTERM),
        ("2026-10-05 17:59", INTERM),
        ("2026-10-05 18:00", PONTA),
        ("2026-10-05 20:59", PONTA),
        ("2026-10-05 21:00", FORA),  # padrao: 21h fora de ponta (nao confirmado)
        ("2026-10-05 22:00", FORA),
    ],
)
def test_branca_preco_por_horario(tarifas: Tarifas, ts: str, esperado: float) -> None:
    assert tarifas.preco_em(pd.Timestamp(ts), BRANCA) == pytest.approx(esperado)


@pytest.mark.parametrize(
    ("ts", "esperado"),
    [
        ("2026-10-05 17:59", INTERM),
        ("2026-10-05 18:00", PONTA),
        ("2026-10-05 20:59", PONTA),
        ("2026-10-05 21:00", INTERM),  # toggle ligado: hora apos a ponta e intermediaria
        ("2026-10-05 21:59", INTERM),
        ("2026-10-05 22:00", FORA),
        ("2026-10-03 21:00", FORA),  # sabado: continua fora de ponta com o toggle
    ],
)
def test_branca_hora_21_toggle(ts: str, esperado: float) -> None:
    ligado = Tarifas.carregar(hora_21_intermediaria=True)
    assert ligado.preco_em(pd.Timestamp(ts), BRANCA) == pytest.approx(esperado)


def test_branca_fim_de_semana_sempre_fora_de_ponta(tarifas: Tarifas) -> None:
    sabado_ponta = pd.Timestamp("2026-10-03 19:00")
    domingo_interm = pd.Timestamp("2026-10-04 17:00")
    assert tarifas.preco_em(sabado_ponta, BRANCA) == pytest.approx(FORA)
    assert tarifas.preco_em(domingo_interm, BRANCA) == pytest.approx(FORA)


def test_feriados_nacionais_2026_lista_do_doc() -> None:
    assert feriados_nacionais(2026) == frozenset(
        date(2026, m, d)
        for m, d in [(1, 1), (2, 17), (4, 3), (4, 21), (5, 1), (6, 4), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
    )


@pytest.mark.parametrize("ts", ["2026-10-12 19:00", "2026-02-17 19:00", "2026-04-03 17:00", "2026-06-04 19:00"])
def test_branca_feriado_nacional_dia_util_e_fora_de_ponta(tarifas: Tarifas, ts: str) -> None:
    assert tarifas.preco_em(pd.Timestamp(ts), BRANCA) == pytest.approx(FORA)


def test_consciencia_negra_nao_esta_na_lista_do_doc(tarifas: Tarifas) -> None:
    # 20/11/2026 e sexta-feira; fora da lista do doc, logo segue o horario normal (ponta).
    assert tarifas.preco_em(pd.Timestamp("2026-11-20 19:00"), BRANCA) == pytest.approx(PONTA)


def _csv(tmp_path: Path, linhas: list[str]) -> Path:
    cab = "modalidade,posto,tarifa_rs_kwh,vigencia_inicio,vigencia_fim\n"
    caminho = tmp_path / "t.csv"
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def test_chave_duplicada_na_mesma_vigencia_e_rejeitada(tmp_path: Path) -> None:
    caminho = _csv(
        tmp_path,
        [
            "branca,ponta,1.0,2026-01-01,2026-12-31",
            "branca,ponta,2.0,2026-01-01,2026-12-31",
        ],
    )
    with pytest.raises(ValueError, match="repetida"):
        Tarifas.carregar(caminho)


def test_selecao_por_data_de_referencia(tmp_path: Path) -> None:
    caminho = _csv(
        tmp_path,
        [
            "branca,ponta,1.0,2025-01-01,2025-12-31",
            "branca,ponta,2.0,2026-01-01,2026-12-31",
        ],
    )
    assert Tarifas.carregar(caminho, date(2025, 6, 1)).preco_posto(BRANCA, "ponta") == 1.0
    assert Tarifas.carregar(caminho, date(2026, 6, 1)).preco_posto(BRANCA, "ponta") == 2.0
    with pytest.raises(ValueError, match="nenhuma tarifa vigente"):
        Tarifas.carregar(caminho, date(2027, 6, 1))
    with pytest.raises(ValueError, match="mais de uma vigencia"):
        Tarifas.carregar(caminho)


def test_gross_up_e_bandeira_padrao_vazios_e_opcionais(tarifas: Tarifas) -> None:
    assert tarifas.gross_up is None and tarifas.bandeira_rs_kwh is None
    assert "SEM tributos e SEM bandeira" in tarifas.descricao_valores()
    com = Tarifas.carregar(gross_up=1.25, bandeira_rs_kwh=0.05)
    assert com.preco_posto(BRANCA, "ponta") == pytest.approx((PONTA + 0.05) * 1.25)
    assert "gross-up" in com.descricao_valores() and "bandeira" in com.descricao_valores()


@pytest.mark.parametrize("gross_up", [0.9, float("nan"), float("inf")])
def test_gross_up_invalido_e_rejeitado(gross_up: float) -> None:
    with pytest.raises(ValueError, match="gross_up"):
        Tarifas.carregar(gross_up=gross_up)
