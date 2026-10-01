"""Previsao do dia seguinte: protocolo, features permitidas e guard de defasagem minima.

Origem = meia-noite; horizonte = as 24 horas do dia. Regra obrigatoria: nenhuma feature da hora
alvo `t` depende de um valor com defasagem menor que `DEFASAGEM_MINIMA_H` (24 h) em relacao a
`t`. Assim toda hora do dia usa so dados disponiveis ate a meia-noite do proprio dia e a previsao
nao precisa ser recursiva. `defasagem_violadora` mede a regra empiricamente (perturba o
passado recente e olha quais features mudam), entao vale para qualquer construtor de features.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from mapen_aconselhamento.domain.calendario import reindexar
from mapen_aconselhamento.domain.features import adicionar_lags
from mapen_modelos.domain.features import ALVO, FREQ, eh_feriado, tipo_dia

DEFASAGEM_MINIMA_H = 24
HORIZONTE_H = 24
DEFASAGENS_PREVISAO: tuple[int, ...] = (24, 48, 168)
JANELA_PREVISAO = 24
MINIMO_PERIODOS_JANELA = 12  # meia janela; media das horas validas, nunca interpolacao
FEATURES_CALENDARIO_PREVISAO: tuple[str, ...] = ("hora", "dia_semana", "feriado", "hora_semana")
FEATURES_LAGS_PREVISAO: tuple[str, ...] = ("kw_lag24", "kw_lag48", "kw_lag168")
FEATURES_JANELA_PREVISAO: tuple[str, ...] = ("kw_media24_d24", "kw_desvio24_d24")
FEATURES_PREVISAO: tuple[str, ...] = (
    FEATURES_CALENDARIO_PREVISAO + FEATURES_LAGS_PREVISAO + FEATURES_JANELA_PREVISAO
)
GRUPOS_FEATURES: dict[str, tuple[str, ...]] = {
    "calendario": FEATURES_CALENDARIO_PREVISAO,
    "lags": FEATURES_LAGS_PREVISAO,
    "janela_movel": FEATURES_JANELA_PREVISAO,
}

ConstrutorFeatures = Callable[[pd.Series, pd.Timestamp, pd.Timestamp], pd.DataFrame]


def montar_features_previsao(serie: pd.Series, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    """Alvo e features de previsao no calendario horario completo [inicio, fim).

    A janela movel e a media/desvio das 24 h que terminam na defasagem 24 (serie deslocada em 24),
    exigindo pelo menos `MINIMO_PERIODOS_JANELA` horas validas; lacuna nunca e interpolada.
    """
    base = reindexar(serie.rename(ALVO).to_frame(), FREQ, inicio, fim)
    quadro = adicionar_lags(base, ALVO, DEFASAGENS_PREVISAO, FREQ)
    atrasada = quadro[ALVO].shift(DEFASAGEM_MINIMA_H)
    janela = atrasada.rolling(JANELA_PREVISAO, min_periods=MINIMO_PERIODOS_JANELA)
    quadro["kw_media24_d24"] = janela.mean()
    quadro["kw_desvio24_d24"] = janela.std()
    indice = pd.DatetimeIndex(quadro.index)
    quadro["hora"] = indice.hour.to_numpy().astype(np.int64)
    quadro["dia_semana"] = indice.dayofweek.to_numpy().astype(np.int64)
    quadro["feriado"] = eh_feriado(indice).astype(np.int64)
    quadro["hora_semana"] = tipo_dia(indice) * 24 + indice.hour.to_numpy().astype(np.int64)
    return quadro[[ALVO, *FEATURES_PREVISAO]]


def naive_sazonal(serie: pd.Series, periodo_h: int, alvo: pd.DatetimeIndex) -> np.ndarray:
    """Valor observado `periodo_h` horas antes de cada hora alvo; NaN se nao houver observacao."""
    if periodo_h < DEFASAGEM_MINIMA_H:
        raise ValueError(f"periodo {periodo_h} h viola a defasagem minima de {DEFASAGEM_MINIMA_H} h")
    anterior = alvo - pd.Timedelta(hours=periodo_h)
    return np.asarray(serie.reindex(anterior).to_numpy(dtype=np.float64), dtype=np.float64)


def defasagem_violadora(
    construtor: ConstrutorFeatures,
    serie: pd.Series,
    minimo_h: int = DEFASAGEM_MINIMA_H,
    salto: float = 1000.0,
) -> list[str]:
    """Features que dependem de um valor com defasagem < `minimo_h` (lista vazia = regra cumprida).

    Para cada defasagem j em [0, minimo_h) soma `salto` ao valor de `serie` em `q` e compara a
    linha `q + j` do quadro de features com a do quadro original. `serie` deve ser completa
    (sem NaN) e longa o bastante para que `q` tenha historico para todas as features.
    """
    inicio = pd.Timestamp(serie.index[0])
    fim = pd.Timestamp(serie.index[-1]) + pd.Timedelta(FREQ)
    base = construtor(serie, inicio, fim)
    meio = len(serie) // 2
    violadoras: set[str] = set()
    for j in range(minimo_h):
        alterada = serie.copy()
        alterada.iloc[meio] = float(alterada.iloc[meio]) + salto
        novo = construtor(alterada, inicio, fim)
        linha_base = base.iloc[meio + j].drop(ALVO, errors="ignore")
        linha_nova = novo.iloc[meio + j].drop(ALVO, errors="ignore")
        for nome in linha_base.index:
            if not np.array_equal(
                np.asarray([linha_base[nome]], dtype=np.float64),
                np.asarray([linha_nova[nome]], dtype=np.float64),
                equal_nan=True,
            ):
                violadoras.add(str(nome))
    return sorted(violadoras)
