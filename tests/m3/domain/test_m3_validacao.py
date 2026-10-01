"""Guard `test_temporal_split_no_leakage` e a referencia ingenua (split aleatorio) que ele deve reprovar."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.validacao import (
    Dobra,
    VazamentoTemporalError,
    dobras_walk_forward,
    verificar_sem_vazamento,
)

INICIO = pd.Timestamp("2026-01-05")
FIM = INICIO + pd.Timedelta(weeks=14)
INDICE = pd.date_range(INICIO, FIM, freq="1h", inclusive="left")

Particao = list[tuple[pd.DatetimeIndex, pd.DatetimeIndex]]


def _split_walk_forward(indice: pd.DatetimeIndex) -> Particao:
    """O gerador real, traduzido para pares (indices de treino, indices de teste)."""
    dobras = dobras_walk_forward(
        pd.Timestamp(indice.min()), pd.Timestamp(indice.max()) + pd.Timedelta("1h"),
        pd.Timedelta(weeks=4), pd.Timedelta(weeks=2),
    )
    return [
        (
            indice[(indice >= d.treino_inicio) & (indice < d.treino_fim)],
            indice[(indice >= d.teste_inicio) & (indice < d.teste_fim)],
        )
        for d in dobras
    ]


def _split_aleatorio_ingenuo(indice: pd.DatetimeIndex) -> Particao:
    """Referencia ruim: embaralha as horas e fatia, como um train_test_split padrao."""
    rng = np.random.default_rng(0)
    ordem = rng.permutation(len(indice))
    corte = int(0.75 * len(indice))
    return [(indice[np.sort(ordem[:corte])], indice[np.sort(ordem[corte:])])]


SPLITTER: Callable[[pd.DatetimeIndex], Particao] = _split_walk_forward


def _afirmar_sem_vazamento(particao: Particao) -> None:
    assert particao, "split vazio"
    for treino, teste in particao:
        assert len(treino.intersection(teste)) == 0, "mesma hora no treino e no teste"
        assert treino.max() < teste.min(), "treino alcanca o periodo de teste"


def test_temporal_split_no_leakage() -> None:
    _afirmar_sem_vazamento(SPLITTER(INDICE))


def test_referencia_aleatoria_vaza() -> None:
    with pytest.raises(AssertionError):
        _afirmar_sem_vazamento(_split_aleatorio_ingenuo(INDICE))


def test_gerador_real_nao_se_sobrepoe_e_verificador_aceita() -> None:
    dobras = dobras_walk_forward(INICIO, FIM, pd.Timedelta(weeks=4), pd.Timedelta(weeks=2))
    assert len(dobras) == 5
    verificar_sem_vazamento(dobras)
    assert all(d.treino_inicio == INICIO and d.treino_fim == d.teste_inicio for d in dobras)
    assert all(a.teste_fim == b.teste_inicio for a, b in zip(dobras, dobras[1:], strict=False))


def test_verificador_reprova_treino_que_invade_o_teste() -> None:
    ruim = [Dobra(INICIO, INICIO + pd.Timedelta(weeks=5), INICIO + pd.Timedelta(weeks=4), INICIO + pd.Timedelta(weeks=6))]
    with pytest.raises(VazamentoTemporalError):
        verificar_sem_vazamento(ruim)


def test_janela_curta_nao_gera_dobra() -> None:
    assert dobras_walk_forward(INICIO, INICIO + pd.Timedelta(weeks=5), pd.Timedelta(weeks=4), pd.Timedelta(weeks=2)) == []
