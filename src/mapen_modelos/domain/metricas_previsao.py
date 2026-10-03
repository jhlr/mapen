"""Metricas de previsao (MAE, RMSE, MASE) e regra de decisao pre-registrada.

Regra (docs/m3_notas.md, "Pre-registro"): um modelo e adotado so se a mediana de MASE no periodo
reservado e pelo menos 10% menor que a do seasonal-naive-168 E ele vence o seasonal-naive-168 em
pelo menos 12 equipamentos. Senao, o modelo mais simples dentro de 5% da melhor mediana.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mapen_modelos.domain.previsao import GRUPOS_FEATURES, naive_sazonal

NAIVE_168 = "seasonal_naive_168"
GANHO_MINIMO = 0.10
VITORIAS_MINIMAS = 12
TOLERANCIA_SIMPLICIDADE = 0.05


@dataclass(frozen=True)
class Metricas:
    mae: float
    rmse: float
    mase: float
    horas: int


def mae(y: np.ndarray, previsto: np.ndarray) -> float:
    return float(np.abs(y - previsto).mean()) if y.size else float("nan")


def rmse(y: np.ndarray, previsto: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - previsto) ** 2))) if y.size else float("nan")


def escala_mase(treino: pd.Series, periodo_h: int = 168) -> float:
    """MAE dentro da amostra do seasonal-naive de `periodo_h` na janela de treino (pares validos)."""
    previsto = naive_sazonal(treino, periodo_h, pd.DatetimeIndex(treino.index))
    y = treino.to_numpy(dtype=np.float64)
    ok = ~np.isnan(y) & ~np.isnan(previsto)
    if not ok.any():
        raise ValueError("sem pares validos para a escala do MASE")
    return float(np.abs(y[ok] - previsto[ok]).mean())


def metricas(y: np.ndarray, previsto: np.ndarray, escala: float) -> Metricas:
    erro = mae(y, previsto)
    mase = erro / escala if escala > 0 else float("nan")
    return Metricas(erro, rmse(y, previsto), mase, int(y.size))


def suporte_comum(y: np.ndarray, previsoes: dict[str, np.ndarray]) -> np.ndarray:
    """Horas com alvo valido e previsao de todos os modelos (comparacao no mesmo conjunto)."""
    ok = ~np.isnan(y)
    for p in previsoes.values():
        ok &= ~np.isnan(p)
    return np.asarray(ok, dtype=np.bool_)


def mediana(valores: dict[str, float]) -> float:
    return float(np.median(list(valores.values())))


@dataclass(frozen=True)
class Decisao:
    adotado: str
    regra_aplicada: str  # "ganho_e_vitorias" | "mais_simples_dentro_de_5pct"
    medianas: dict[str, float]
    vitorias_vs_naive168: dict[str, int]
    vitorias_melhor_de_todos: dict[str, int]
    passaram: list[str]
    melhor_mediana: str
    motivo: str


def decidir_adocao(
    mase: dict[str, dict[str, float]],
    ordem_simplicidade: tuple[str, ...],
    referencia: str = NAIVE_168,
) -> Decisao:
    """Aplica a regra pre-registrada. `mase[modelo][equipamento]`; `ordem_simplicidade` do mais simples."""
    if set(mase) != set(ordem_simplicidade) or referencia not in mase:
        raise ValueError("ordem_simplicidade deve listar exatamente os modelos, incluindo a referencia")
    equipamentos = sorted(mase[referencia])
    medianas = {m: mediana(mase[m]) for m in mase}
    vitorias = {
        m: sum(1 for e in equipamentos if mase[m][e] < mase[referencia][e]) for m in mase if m != referencia
    }
    melhor_de_todos = dict.fromkeys(mase, 0)
    for e in equipamentos:
        melhor_de_todos[min(mase, key=lambda m: mase[m][e])] += 1
    passaram = [
        m
        for m in ordem_simplicidade
        if m != referencia
        and medianas[m] <= (1.0 - GANHO_MINIMO) * medianas[referencia]
        and vitorias[m] >= VITORIAS_MINIMAS
    ]
    if passaram:
        melhor_passou = min(medianas[m] for m in passaram)
        adotado = next(m for m in passaram if medianas[m] <= (1.0 + TOLERANCIA_SIMPLICIDADE) * melhor_passou)
        regra = "ganho_e_vitorias"
        motivo = (
            f"{adotado}: mediana de MASE {medianas[adotado]:.4f} vs {medianas[referencia]:.4f} do {referencia} "
            f"e {vitorias[adotado]}/{len(equipamentos)} vitorias"
        )
    else:
        melhor = min(medianas, key=lambda m: medianas[m])
        adotado = next(
            m for m in ordem_simplicidade if medianas[m] <= (1.0 + TOLERANCIA_SIMPLICIDADE) * medianas[melhor]
        )
        regra = "mais_simples_dentro_de_5pct"
        motivo = (
            f"nenhum candidato passou a regra de ganho (>= 10% e >= 12 vitorias); "
            f"melhor mediana: {melhor} ({medianas[melhor]:.4f}); adotado o mais simples dentro de 5%: {adotado}"
        )
    melhor_mediana = min(medianas, key=lambda m: medianas[m])
    return Decisao(adotado, regra, medianas, vitorias, melhor_de_todos, passaram, melhor_mediana, motivo)


def participacao_por_grupo(por_feature: dict[str, float]) -> dict[str, float]:
    """Soma a participacao no |SHAP| por grupo (calendario, lags, janela movel)."""
    return {g: float(sum(por_feature.get(f, 0.0) for f in fs)) for g, fs in GRUPOS_FEATURES.items()}
