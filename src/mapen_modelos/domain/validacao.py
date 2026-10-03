"""Validacao temporal walk-forward com janela de treino expansiva.

Cada dobra treina em [treino_inicio, treino_fim) e testa em [teste_inicio, teste_fim), com
`treino_fim == teste_inicio`: nada do teste (nem do futuro) entra no treino.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Dobra:
    treino_inicio: pd.Timestamp
    treino_fim: pd.Timestamp
    teste_inicio: pd.Timestamp
    teste_fim: pd.Timestamp


def dobras_walk_forward(
    inicio: pd.Timestamp,
    fim: pd.Timestamp,
    treino_inicial: pd.Timedelta,
    teste: pd.Timedelta,
    passo: pd.Timedelta | None = None,
) -> list[Dobra]:
    """Dobras expansivas ancoradas em `inicio`; so dobras de teste completas dentro de [inicio, fim)."""
    passo = teste if passo is None else passo
    if treino_inicial <= pd.Timedelta(0) or teste <= pd.Timedelta(0) or passo <= pd.Timedelta(0):
        raise ValueError("treino_inicial, teste e passo devem ser positivos")
    dobras: list[Dobra] = []
    corte = inicio + treino_inicial
    while corte + teste <= fim:
        dobras.append(Dobra(inicio, corte, corte, corte + teste))
        corte = corte + passo
    return dobras


class VazamentoTemporalError(ValueError):
    """Uma dobra deixa o treino tocar o teste ou o futuro dele."""


def verificar_sem_vazamento(dobras: list[Dobra]) -> None:
    """Falha se alguma dobra tem treino que alcanca o teste ou se o teste nao avanca no tempo."""
    anterior_fim: pd.Timestamp | None = None
    for k, d in enumerate(dobras):
        if not d.treino_inicio < d.treino_fim <= d.teste_inicio < d.teste_fim:
            raise VazamentoTemporalError(f"dobra {k}: treino precisa terminar antes do inicio do teste")
        if anterior_fim is not None and d.teste_inicio < anterior_fim:
            raise VazamentoTemporalError(f"dobra {k}: testes se sobrepoem")
        anterior_fim = d.teste_fim
