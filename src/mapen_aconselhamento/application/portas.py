"""Portas do caso de uso: o que a aplicacao precisa do mundo externo."""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class RepositorioLeituras(Protocol):
    def ler_leituras(self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
        """Leituras de um predio em [inicio, fim): colunas ts, equipamento_id, kwh, ausente."""
        ...

    def ler_duplicados(self, sensor_id: str) -> tuple[int, str] | None:
        """(timestamps duplicados descartados, politica) da ultima carga do predio, ou None."""
        ...
