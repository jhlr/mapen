"""Features por serie de equipamento, sempre sobre o calendario horario completo.

Lag, calendario e feriados vem do M1 (`adicionar_lags`, `reindexar`, `feriados_nacionais`):
uma lacuna vira NaN e propaga NaN para os lags e as janelas que a referenciam. Toda feature
da linha `t` usa so valores de `t-1` para tras (a janela movel e calculada sobre a serie
deslocada em 1), entao nao ha vazamento do proprio alvo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mapen_aconselhamento.domain.calendario import reindexar
from mapen_aconselhamento.domain.features import adicionar_lags
from mapen_aconselhamento.domain.tarifa import feriados_nacionais

FREQ = "1h"
ALVO = "kw"
DEFASAGENS: tuple[int, ...] = (1, 24, 168)
JANELA_MOVEL = 24
FEATURES_CALENDARIO: tuple[str, ...] = ("hora", "dia_semana", "feriado")
FEATURES_HISTORICO: tuple[str, ...] = (
    "kw_lag1",
    "kw_lag24",
    "kw_lag168",
    "kw_media24",
    "kw_desvio24",
)
FEATURES: tuple[str, ...] = FEATURES_CALENDARIO + FEATURES_HISTORICO
HORAS_POR_SEMANA = 168


def eh_feriado(indice: pd.DatetimeIndex) -> np.ndarray:
    """True para os feriados nacionais da lista do M1 (mesmo calendario da tarifa)."""
    anos = [int(a) for a in indice.year.unique()]
    feriados = pd.DatetimeIndex(sorted(f for a in anos for f in feriados_nacionais(a)))
    return np.asarray(indice.normalize().isin(feriados))


def tipo_dia(indice: pd.DatetimeIndex) -> np.ndarray:
    """Dia da semana (0=segunda) com feriado nacional tratado como domingo (6)."""
    dias = indice.dayofweek.to_numpy().astype(np.int64)
    return np.where(eh_feriado(indice), 6, dias)


def montar_features(serie: pd.Series, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    """Alvo e features no calendario horario completo [inicio, fim).

    `serie` e kW por hora, com indice horario sem repeticao; horas ausentes viram NaN.
    """
    base = reindexar(serie.rename(ALVO).to_frame(), FREQ, inicio, fim)
    quadro = adicionar_lags(base, ALVO, DEFASAGENS, FREQ)
    passado = quadro[ALVO].shift(1)
    janela = passado.rolling(JANELA_MOVEL, min_periods=JANELA_MOVEL)
    quadro["kw_media24"] = janela.mean()
    quadro["kw_desvio24"] = janela.std()
    indice = pd.DatetimeIndex(quadro.index)
    quadro["hora"] = indice.hour.to_numpy().astype(np.int64)
    quadro["dia_semana"] = indice.dayofweek.to_numpy().astype(np.int64)
    quadro["feriado"] = eh_feriado(indice).astype(np.int64)
    return quadro[[ALVO, *FEATURES]]
