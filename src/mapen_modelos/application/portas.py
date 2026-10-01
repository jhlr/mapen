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
