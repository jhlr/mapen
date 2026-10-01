"""Explicacao: top features por contribuicao SHAP e checagem D7 (identidade de calendario).

Os valores SHAP chegam como matriz (linhas x features) pela porta `Explicador`; aqui so ha
calculo puro.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mapen_modelos.domain.features import FEATURES_CALENDARIO

LIMIAR_FEATURE_DOMINANTE = 0.5


@dataclass(frozen=True)
class ContribuicaoFeature:
    feature: str
    shap: float


@dataclass(frozen=True)
class ChecagemD7:
    """Participacao no |SHAP| total: calendario x historico (lag/janela)."""

    participacao_calendario: float
    participacao_historico: float
    participacao_por_feature: dict[str, float]
    feature_dominante: str | None
    avisos: list[str]


def top_features(
    shap_linha: np.ndarray, nomes: tuple[str, ...], n: int = 3
) -> list[ContribuicaoFeature]:
    """As `n` features de maior |SHAP| de uma linha."""
    if shap_linha.shape != (len(nomes),):
        raise ValueError("shap_linha e nomes precisam ter o mesmo tamanho")
    ordem = np.argsort(-np.abs(shap_linha), kind="stable")[:n]
    return [ContribuicaoFeature(nomes[i], float(shap_linha[i])) for i in ordem]


def checar_d7(
    shap_valores: np.ndarray,
    nomes: tuple[str, ...],
    calendario: tuple[str, ...] = FEATURES_CALENDARIO,
    limiar: float = LIMIAR_FEATURE_DOMINANTE,
) -> ChecagemD7:
    """Participacao no |SHAP| medio por feature; avisa quando uma unica feature passa de `limiar`.

    D7: a atribuicao nao deve ser dominada por identidade de calendario. Como o modelo e por
    equipamento, a identidade do equipamento nao e feature; "identidade" aqui e hora, dia da
    semana e feriado (o que um baseline sazonal ja explica).
    """
    if shap_valores.ndim != 2 or shap_valores.shape[1] != len(nomes):
        raise ValueError("shap_valores deve ser (linhas, len(nomes))")
    media_abs = np.abs(shap_valores).mean(axis=0)
    total = float(media_abs.sum())
    if total <= 0.0:
        return ChecagemD7(0.0, 0.0, {n: 0.0 for n in nomes}, None, ["SHAP total nulo: sem atribuicao"])
    por_feature = {n: float(v / total) for n, v in zip(nomes, media_abs, strict=True)}
    cal = sum(por_feature[n] for n in nomes if n in calendario)
    avisos: list[str] = []
    dominante: str | None = None
    maior = max(por_feature, key=lambda k: por_feature[k])
    if por_feature[maior] > limiar:
        dominante = maior
        avisos.append(f"feature unica domina a atribuicao: {maior} = {por_feature[maior]:.1%} (> {limiar:.0%})")
    return ChecagemD7(float(cal), float(1.0 - cal), por_feature, dominante, avisos)
