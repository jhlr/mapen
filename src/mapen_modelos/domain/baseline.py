"""Baseline sazonal: kW esperado por hora da semana, estimado so na janela de treino.

O "tipo de dia" trata feriado nacional como domingo, entao a feriado entra no calendario do
baseline. O z-score e (observado - esperado) / desvio do mesmo horario da semana no treino.
Baseline fraca: menos de `SEMANAS_MINIMAS` semanas completas na janela de treino.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mapen_modelos.domain.features import HORAS_POR_SEMANA, tipo_dia

SEMANAS_MINIMAS = 4
COBERTURA_SEMANA_COMPLETA = 0.9
MINIMO_AMOSTRAS_DESVIO = 3
PISO_DESVIO_RELATIVO = 0.05
PISO_DESVIO_ABSOLUTO_KW = 0.01


@dataclass(frozen=True)
class BaselineSazonal:
    """Esperado e desvio por hora da semana (168 posicoes, indice = tipo_dia * 24 + hora)."""

    esperado: np.ndarray
    desvio: np.ndarray
    janela_inicio: pd.Timestamp
    janela_fim: pd.Timestamp
    semanas_completas: int
    fraca: bool


def _posicao(indice: pd.DatetimeIndex) -> np.ndarray:
    return tipo_dia(indice) * 24 + indice.hour.to_numpy().astype(np.int64)


def contar_semanas_completas(
    serie: pd.Series, cobertura_minima: float = COBERTURA_SEMANA_COMPLETA
) -> int:
    """Blocos consecutivos de 168 h a partir do inicio com pelo menos `cobertura_minima` de horas validas.

    Um bloco final incompleto (menos de 168 h) nao conta.
    """
    validos = serie.notna().to_numpy()
    blocos = len(validos) // HORAS_POR_SEMANA
    contagem = 0
    for b in range(blocos):
        fatia = validos[b * HORAS_POR_SEMANA : (b + 1) * HORAS_POR_SEMANA]
        if fatia.mean() >= cobertura_minima:
            contagem += 1
    return contagem


def ajustar_baseline(
    treino: pd.Series,
    semanas_minimas: int = SEMANAS_MINIMAS,
    cobertura_minima: float = COBERTURA_SEMANA_COMPLETA,
) -> BaselineSazonal:
    """Ajusta o baseline na serie de treino (calendario horario completo, NaN nas lacunas)."""
    if treino.empty:
        raise ValueError("janela de treino vazia")
    indice = pd.DatetimeIndex(treino.index)
    valores = treino.to_numpy(dtype=np.float64)
    posicao = _posicao(indice)
    valido = ~np.isnan(valores)
    if not valido.any():
        raise ValueError("janela de treino sem nenhum valor valido")
    media_global = float(valores[valido].mean())
    desvio_global = float(valores[valido].std(ddof=1)) if valido.sum() > 1 else 0.0
    piso = max(PISO_DESVIO_RELATIVO * abs(media_global), PISO_DESVIO_ABSOLUTO_KW)
    esperado = np.full(HORAS_POR_SEMANA, media_global)
    desvio = np.full(HORAS_POR_SEMANA, max(desvio_global, piso))
    for p in range(HORAS_POR_SEMANA):
        amostra = valores[valido & (posicao == p)]
        if amostra.size >= 1:
            esperado[p] = amostra.mean()
        if amostra.size >= MINIMO_AMOSTRAS_DESVIO:
            desvio[p] = max(float(amostra.std(ddof=1)), piso)
    semanas = contar_semanas_completas(treino, cobertura_minima)
    fim = pd.Timestamp(indice.max()) + pd.Timedelta("1h")
    return BaselineSazonal(
        esperado=esperado,
        desvio=desvio,
        janela_inicio=pd.Timestamp(indice.min()),
        janela_fim=fim,
        semanas_completas=semanas,
        fraca=semanas < semanas_minimas,
    )


def esperado_em(baseline: BaselineSazonal, indice: pd.DatetimeIndex) -> np.ndarray:
    """kW esperado em cada timestamp."""
    return np.asarray(baseline.esperado[_posicao(indice)], dtype=np.float64)


def zscore(baseline: BaselineSazonal, serie: pd.Series) -> pd.Series:
    """Residuo padronizado (observado - esperado) / desvio do horario da semana; NaN onde falta dado."""
    indice = pd.DatetimeIndex(serie.index)
    posicao = _posicao(indice)
    z = (serie.to_numpy(dtype=np.float64) - baseline.esperado[posicao]) / baseline.desvio[posicao]
    return pd.Series(z, index=serie.index, name="z")
