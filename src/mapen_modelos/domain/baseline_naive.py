"""Baseline dos alertas z-score: seasonal-naive-168 com escala refeita toda semana.

Esperado de uma hora = valor observado 168 h antes (a mesma hora da semana passada). O estudo
de previsao pre-registrado (docs/m3_notas.md) mostrou que a media estatica por hora da semana e
o pior candidato (mediana de MASE 1,75) e que o naive-168 bate todos, porque se adapta a deriva
de regime sem ajuste. O naive-168 nao tem parametro; o que se refaz e a escala.

Escala: desvio dos residuos `observado - observado(t-168)` na mesma hora da semana, estimado so
com residuos anteriores ao inicio da semana do alvo (refit semanal, expansivo). Residuos de horas
que ja viraram alerta ficam fora das semanas seguintes (senao o proprio incidente inflaria a
escala e esconderia o seguinte). O residuo de uma hora ainda carrega o valor de 168 h antes, entao
um evento alerta duas vezes: na hora e uma semana depois (ver `zona_contaminada` do benchmark).
Feriado nao e tratado como domingo aqui: o naive-168 compara com a mesma hora da semana passada.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mapen_modelos.domain.anomalia import LIMIAR_Z_PADRAO
from mapen_modelos.domain.baseline import (
    MINIMO_AMOSTRAS_DESVIO,
    PISO_DESVIO_ABSOLUTO_KW,
    PISO_DESVIO_RELATIVO,
    SEMANAS_MINIMAS,
    contar_semanas_completas,
)
from mapen_modelos.domain.features import FREQ, HORAS_POR_SEMANA

NOME_BASELINE = "seasonal_naive_168"


@dataclass(frozen=True)
class ZScoreNaive:
    """Esperado, escala e z de cada hora do periodo [inicio, fim), alinhados a `indice`."""

    indice: pd.DatetimeIndex
    esperado: np.ndarray
    sigma: np.ndarray
    z: np.ndarray
    janela_inicio: pd.Timestamp  # primeiro instante da serie usada como historico
    janela_fim: np.ndarray  # por hora: inicio da semana do alvo (fim exclusivo do historico da escala)
    fraca: np.ndarray  # por hora: menos de SEMANAS_MINIMAS semanas completas de residuo no historico


def _posicao(indice: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(indice.dayofweek.to_numpy() * 24 + indice.hour.to_numpy(), dtype=np.int64)


def _sigma_por_posicao(
    residuo: np.ndarray, posicao: np.ndarray, usar: np.ndarray, nivel: float
) -> np.ndarray:
    """Desvio do residuo por hora da semana (168); cai para o desvio global e respeita um piso."""
    piso = max(PISO_DESVIO_RELATIVO * abs(nivel), PISO_DESVIO_ABSOLUTO_KW)
    amostra = residuo[usar]
    global_ = float(amostra.std(ddof=1)) if amostra.size > 1 else 0.0
    sigma = np.full(HORAS_POR_SEMANA, max(global_, piso))
    for p in range(HORAS_POR_SEMANA):
        valores = residuo[usar & (posicao == p)]
        if valores.size >= MINIMO_AMOSTRAS_DESVIO:
            sigma[p] = max(float(valores.std(ddof=1)), piso)
    return sigma


def zscore_naive168(
    serie: pd.Series,
    inicio: pd.Timestamp,
    fim: pd.Timestamp,
    limiar: float = LIMIAR_Z_PADRAO,
) -> ZScoreNaive:
    """z-score do residuo contra o naive-168 em [inicio, fim), com a escala refeita a cada semana.

    `serie` e kW por hora e deve cobrir o historico antes de `inicio` (quanto mais, melhor a
    escala); lacunas viram NaN e hora sem observado ou sem referencia fica com z NaN (nunca
    interpolada). As semanas do alvo sao blocos de 168 h a partir de `inicio`.
    """
    if inicio < pd.Timestamp(serie.index.min()):
        raise ValueError("a serie precisa comecar antes do inicio do periodo")
    completo = pd.date_range(pd.Timestamp(serie.index.min()), fim, freq=FREQ, inclusive="left")
    y = serie.reindex(completo).to_numpy(dtype=np.float64)
    referencia = np.full_like(y, np.nan)
    referencia[HORAS_POR_SEMANA:] = y[:-HORAS_POR_SEMANA]
    residuo = y - referencia
    posicao = _posicao(completo)
    valido = ~np.isnan(residuo)
    alerta = np.zeros(len(y), dtype=bool)
    primeiro = int(completo.get_indexer(pd.DatetimeIndex([inicio]))[0])
    total = len(y) - primeiro
    esperado = referencia[primeiro:].copy()
    sigma = np.empty(total)
    z = np.full(total, np.nan)
    janela_fim = np.empty(total, dtype="datetime64[ns]")
    fraca = np.empty(total, dtype=bool)
    for s in range(primeiro, len(y), HORAS_POR_SEMANA):
        e = min(s + HORAS_POR_SEMANA, len(y))
        historico = valido[:s] & ~alerta[:s]
        nivel_valido = y[:s][~np.isnan(y[:s])]
        nivel = float(nivel_valido.mean()) if nivel_valido.size else 0.0
        sigma_semana = _sigma_por_posicao(residuo[:s], posicao[:s], historico, nivel)
        semanas = contar_semanas_completas(pd.Series(residuo[:s], index=completo[:s]))
        for i in range(s, e):
            k = i - primeiro
            sigma[k] = sigma_semana[posicao[i]]
            if valido[i]:
                z[k] = residuo[i] / sigma[k]
                alerta[i] = abs(z[k]) >= limiar
        janela_fim[s - primeiro : e - primeiro] = np.datetime64(completo[s])
        fraca[s - primeiro : e - primeiro] = semanas < SEMANAS_MINIMAS
    return ZScoreNaive(
        indice=completo[primeiro:],
        esperado=esperado,
        sigma=sigma,
        z=z,
        janela_inicio=pd.Timestamp(completo[0]),
        janela_fim=janela_fim,
        fraca=fraca,
    )
