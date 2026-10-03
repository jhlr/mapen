"""Antes x depois com grupo-controle: deriva conhecida + reducao conhecida, selecao de controles e ausencia de controle."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.comparacao import (
    NOME_METODO_CONTROLE,
    aplicar_reducao,
    comparar_antes_depois,
    comparar_com_controle,
    correlacao_perfil,
    resumir_varredura,
    selecionar_controles,
)

INICIO = pd.Timestamp("2026-02-02")  # segunda-feira
SEMANAS_PRE = 10  # treino; antes = semanas 8-9; depois = semanas 10-11
SEMANAS = 12
FIM_ANTES = INICIO + pd.Timedelta(weeks=SEMANAS_PRE)
INICIO_ANTES = FIM_ANTES - pd.Timedelta(weeks=2)
FIM_DEPOIS = FIM_ANTES + pd.Timedelta(weeks=2)
REDUCAO = 0.15
TOLERANCIA_PP = 3.0
# deriva semanal de nivel comum: o depois fica 40% acima do antes
FATORES = np.array([1.0, 1.3, 0.8, 1.2, 0.9, 1.4, 1.0, 1.1, 1.0, 1.0, 1.4, 1.4])


def _padrao(idx: pd.DatetimeIndex, pico: float, base: float) -> np.ndarray:
    util = (idx.dayofweek.to_numpy() < 5) & (idx.hour.to_numpy() >= 8) & (idx.hour.to_numpy() < 18)
    return np.where(util, pico, base)


def _serie(pico: float, base: float, fatores: np.ndarray, semente: int) -> pd.Series:
    idx = pd.date_range(INICIO, periods=168 * SEMANAS, freq="1h")
    por_hora = np.repeat(fatores, 168)
    ruido = np.random.default_rng(semente).normal(0.0, 0.02, len(idx))
    return pd.Series(_padrao(idx, pico, base) * por_hora * (1.0 + ruido), index=idx)


def _mundo() -> dict[str, pd.Series]:
    indep = np.random.default_rng(99).uniform(0.7, 1.3, SEMANAS)
    indep[SEMANAS_PRE:] = 1.0
    return {
        "tratado": _serie(5.0, 1.0, FATORES, 1),
        "c1": _serie(8.0, 2.0, FATORES, 2),
        "c2": _serie(3.0, 0.5, FATORES, 3),
        "alheio": _serie(4.0, 1.0, indep, 4),  # sem a deriva compartilhada
    }


def _periodos(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    return s[(s.index >= INICIO_ANTES) & (s.index < FIM_ANTES)], s[(s.index >= FIM_ANTES) & (s.index < FIM_DEPOIS)]


def _pre(s: pd.Series) -> pd.Series:
    return s[s.index < FIM_ANTES]


def _hora_da_semana(i: pd.DatetimeIndex) -> pd.Index[int]:
    return pd.Index(i.dayofweek * 24 + i.hour)


def _recuperado_baseline_antigo(mundo: dict[str, pd.Series]) -> float:
    """Metodo antigo: esperado = perfil sazonal do treino (semanas 0-7), sem deriva."""
    treino = mundo["tratado"][mundo["tratado"].index < INICIO_ANTES]
    perfil = treino.groupby(_hora_da_semana(pd.DatetimeIndex(treino.index))).mean()
    tratado = aplicar_reducao(mundo["tratado"], FIM_ANTES, REDUCAO)
    antes, depois = _periodos(tratado)
    esp_a = pd.Series(perfil.reindex(_hora_da_semana(pd.DatetimeIndex(antes.index))).to_numpy(), index=antes.index)
    esp_d = pd.Series(perfil.reindex(_hora_da_semana(pd.DatetimeIndex(depois.index))).to_numpy(), index=depois.index)
    return comparar_antes_depois(antes, esp_a, depois, esp_d, False).economia_pct


def _recuperado_controle(mundo: dict[str, pd.Series]) -> float:
    tratado = aplicar_reducao(mundo["tratado"], FIM_ANTES, REDUCAO)
    controles = selecionar_controles("tratado", {k: _pre(v) for k, v in {**mundo, "tratado": tratado}.items()})
    ca = {c: _periodos(mundo[c])[0] for c in controles}
    cd = {c: _periodos(mundo[c])[1] for c in controles}
    antes, depois = _periodos(tratado)
    return comparar_com_controle(antes, depois, ca, cd, False).economia_pct


def test_controle_recupera_reducao_conhecida_sob_deriva() -> None:
    assert _recuperado_controle(_mundo()) == pytest.approx(100.0 * REDUCAO, abs=TOLERANCIA_PP)


def test_metodo_antigo_nao_recupera_sob_a_mesma_deriva() -> None:
    erro = abs(_recuperado_baseline_antigo(_mundo()) - 100.0 * REDUCAO)
    assert erro > TOLERANCIA_PP


def test_selecao_exclui_o_tratado_e_ignora_series_sem_correlacao() -> None:
    mundo = _mundo()
    pre = {k: _pre(v) for k, v in mundo.items()}
    escolhidos = selecionar_controles("tratado", pre)
    assert "tratado" not in escolhidos
    assert set(escolhidos) == {"c1", "c2"}
    # o tratado correlaciona perfeitamente consigo mesmo: so a exclusao explicita o tira
    assert correlacao_perfil(pre["tratado"], pre["tratado"]) == pytest.approx(1.0)
    assert correlacao_perfil(pre["tratado"], pre["alheio"]) < 0.5


def test_selecao_respeita_limite_e_ordem_por_correlacao() -> None:
    mundo = _mundo()
    pre = {k: _pre(v) for k, v in mundo.items()}
    um = selecionar_controles("tratado", pre, n_controles=1, correlacao_minima=0.0)
    assert len(um) == 1 and um[0] in {"c1", "c2"}
    todos = selecionar_controles("tratado", pre, n_controles=3, correlacao_minima=-1.0)
    corr = [correlacao_perfil(pre["tratado"], pre[c]) for c in todos]
    assert corr == sorted(corr, reverse=True)


def test_sem_controle_valido_devolve_nan_com_motivo() -> None:
    mundo = _mundo()
    pre = {"tratado": _pre(mundo["tratado"]), "alheio": _pre(mundo["alheio"])}
    assert selecionar_controles("tratado", pre) == ()
    antes, depois = _periodos(mundo["tratado"])
    r = comparar_com_controle(antes, depois, {}, {}, baseline_fraca=True)
    assert r.metodo == NOME_METODO_CONTROLE
    assert np.isnan(r.economia_pct) and r.controles == () and r.baseline_fraca
    assert r.motivo_invalido == "sem controle valido"


def test_selecao_sem_nenhum_candidato_e_alvo_ausente() -> None:
    mundo = _mundo()
    assert selecionar_controles("tratado", {"tratado": _pre(mundo["tratado"])}) == ()
    with pytest.raises(ValueError):
        selecionar_controles("x", {"tratado": _pre(mundo["tratado"])})
    with pytest.raises(ValueError):
        selecionar_controles("tratado", {"tratado": _pre(mundo["tratado"])}, n_controles=0)


def test_controle_exige_mesmos_controles_em_antes_e_depois() -> None:
    mundo = _mundo()
    a, d = _periodos(mundo["tratado"])
    ca, _ = _periodos(mundo["c1"])
    with pytest.raises(ValueError):
        comparar_com_controle(a, d, {"c1": ca}, {}, False)


def test_resumir_varredura_conta_nan_como_fora() -> None:
    v = resumir_varredura({"a": 15.5, "b": 20.0, "c": float("nan")}, 15.0, 3.0)
    assert (v.avaliados, v.dentro_da_tolerancia, v.sem_resultado) == (3, 1, ("c",))
    assert v.erro_abs_mediano_pp == pytest.approx(2.75) and v.erro_abs_maximo_pp == pytest.approx(5.0)
