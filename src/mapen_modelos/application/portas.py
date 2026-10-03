"""Portas do M3: o que a aplicacao precisa do mundo externo."""

from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd


class LeitorSeries(Protocol):
    def ler_series_horarias(
        self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp
    ) -> pd.DataFrame:
        """kW medio por hora em [inicio, fim): indice horario completo, uma coluna por equipamento.

        Hora sem leitura completa e NaN (nunca interpolada).
        """
        ...


class Regressor(Protocol):
    def prever(self, x: pd.DataFrame) -> np.ndarray:
        """Previsao de kW para cada linha de `x`."""
        ...


class TreinadorModelo(Protocol):
    def treinar(self, x: pd.DataFrame, y: pd.Series) -> Regressor:
        """Treina um modelo para um unico equipamento."""
        ...


class Explicador(Protocol):
    def valores(self, modelo: Regressor, x: pd.DataFrame) -> np.ndarray:
        """Valores SHAP (linhas x features, mesma ordem de colunas de `x`)."""
        ...


class Previsor(Protocol):
    """Previsor do dia seguinte para uma serie horaria (um equipamento).

    Contrato: ajusta so com observacoes anteriores a `treino_fim`; a previsao de cada hora alvo
    usa so observacoes ate a meia-noite do dia dela e, para features, so defasagens >= 24 h.
    `serie` e horaria, completa (NaN nas lacunas) e pode conter valores posteriores ao alvo: o
    previsor nao pode le-los (um teste confere isso adulterando dados a partir da meia-noite).
    `alvo` e uma sequencia de dias inteiros, hora a hora.
    """

    @property
    def nome(self) -> str: ...

    def prever(self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> pd.Series:
        """kW previsto em cada hora de `alvo` (NaN onde o previsor nao consegue prever)."""
        ...


class PrevisorExplicavel(Previsor, Protocol):
    """Previsor cujas previsoes se decompoem em contribuicoes por feature (SHAP)."""

    def contribuicoes(
        self, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """Contribuicao por feature em cada hora de `alvo` (colunas = nomes das features)."""
        ...
