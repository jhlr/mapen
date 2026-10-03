"""Previsor ETS (statsmodels `ETSModel`): erro aditivo, sazonalidade aditiva de periodo 24.

Periodo 168 foi descartado: 168 estados sazonais por equipamento, com 18 semanas de treino
(18 ciclos) e estimacao numerica de 168 valores iniciais, e instavel e lento. Em vez disso o
ajuste ajusta o efeito do tipo de dia: uma serie ETS-24 por tipo de dia (dia util, sabado,
domingo ou feriado), formada pela concatenacao dos dias completos daquele tipo. A previsao do
dia D e o proximo dia na serie do seu tipo, entao a memoria de "segunda parecida com terca" e
"domingo parecido com feriado" vem do calendario, nao de um ciclo de 168 estados.

Lacunas: um dia com qualquer hora ausente e descartado da serie do seu tipo (nada e
interpolado). Os parametros de suavizacao e os estados iniciais sao estimados uma vez por tipo
na janela de treino; para cada dia alvo o filtro e reaplicado (`smooth`) sobre os dias do tipo
anteriores a esse dia (so dados ate a meia-noite). Tipo cuja serie de treino e constante (verossimilhanca degenerada: log de variancia zero) repete o
ultimo dia do tipo. Tipo com menos de `DIAS_MINIMOS` dias
validos no treino nao e previsto (NaN).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

from mapen_modelos.domain.features import tipo_dia

PERIODO = 24
DIAS_MINIMOS = 7
# maxfun alto: o gradiente numerico de ~27 parametros esgota o limite padrao (15000 avaliacoes) antes
# de convergir quando alpha cola no limite superior (observado em z2_Light, dia util).
MAX_ITERACOES = 1000
MAX_AVALIACOES = 100_000
VARIACAO_MINIMA_KW = 1e-9


def _tipo3(indice: pd.DatetimeIndex) -> np.ndarray:
    """0 = dia util, 1 = sabado, 2 = domingo ou feriado (tipo_dia do M1: feriado vale domingo)."""
    d = tipo_dia(indice)
    return np.asarray(np.where(d <= 4, 0, d - 4), dtype=np.int64)


def _tipo_do_dia(dia: pd.Timestamp) -> int:
    return int(_tipo3(pd.DatetimeIndex([dia]))[0])


def _modelo(y: np.ndarray) -> ETSModel:
    return ETSModel(
        y, error="add", trend=None, seasonal="add", seasonal_periods=PERIODO, initialization_method="estimated"
    )


class PrevisorETS:
    """Adaptador da porta `Previsor`."""

    nome = "ets_24_tipo_dia"

    def __init__(self) -> None:
        self.ajustes_sem_convergencia = 0  # contagem; o aviso do statsmodels continua visivel

    def prever(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.Series:
        dias = self._dias_completos(serie)
        previsto = np.full(len(alvo), np.nan)
        parametros: dict[int, np.ndarray | None] = {}
        for t in range(3):
            treino = [y for d, y in dias if _tipo_do_dia(d) == t and d + pd.Timedelta(days=1) <= treino_fim]
            if len(treino) < DIAS_MINIMOS:
                continue
            serie_tipo = np.concatenate(treino)
            if np.ptp(serie_tipo) <= VARIACAO_MINIMA_KW:
                parametros[t] = None  # serie constante: verossimilhanca degenerada, vale o ultimo dia do tipo
                continue
            ajuste = _modelo(serie_tipo).fit(disp=False, maxiter=MAX_ITERACOES, maxfun=MAX_AVALIACOES)
            if not ajuste.mle_retvals["converged"]:
                self.ajustes_sem_convergencia += 1
            parametros[t] = np.asarray(ajuste.params, dtype=np.float64)
        for dia in pd.DatetimeIndex(alvo.normalize().unique()):
            t = _tipo_do_dia(pd.Timestamp(dia))
            historico = [y for d, y in dias if _tipo_do_dia(d) == t and d < dia]
            if t not in parametros or len(historico) < DIAS_MINIMOS:
                continue
            horas = np.asarray((alvo >= dia) & (alvo < dia + pd.Timedelta(days=1)))
            ajustados = parametros[t]
            if ajustados is None:
                dia_previsto = historico[-1]
            else:
                resultado = _modelo(np.concatenate(historico)).smooth(ajustados)
                dia_previsto = np.asarray(resultado.forecast(PERIODO), dtype=np.float64)
            previsto[horas] = dia_previsto[alvo[horas].hour]
        return pd.Series(previsto, index=alvo)

    @staticmethod
    def _dias_completos(serie: pd.Series) -> list[tuple[pd.Timestamp, np.ndarray]]:
        """Dias completos (24 horas validas) em ordem: (dia, vetor de 24 kW). Dia com lacuna e descartado."""
        indice = pd.DatetimeIndex(serie.index)
        dias: list[tuple[pd.Timestamp, np.ndarray]] = []
        for dia, grupo in serie.groupby(indice.normalize()):
            valores = grupo.to_numpy(dtype=np.float64)
            if len(valores) == PERIODO and not np.isnan(valores).any():
                dias.append((pd.Timestamp(dia), valores))
        return dias
