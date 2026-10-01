"""Leitor de series horarias sobre a tabela `leitura` do M1 (DuckDB).

Agrega o minuto em hora: so vale a hora com os 60 minutos presentes (kW medio = soma de kWh da
hora). Qualquer minuto ausente torna a hora NaN; nada e interpolado.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from mapen_aconselhamento.domain.calendario import reindexar

MINUTOS_POR_HORA = 60

_SQL = """
SELECT equipamento_id, date_trunc('hour', ts) AS hora, sum(kwh) AS kwh, count(kwh) AS n
FROM leitura
WHERE sensor_id = ? AND ts >= ? AND ts < ?
GROUP BY equipamento_id, date_trunc('hour', ts)
"""


class SeriesHorariasDuckDB:
    """Adaptador da porta `LeitorSeries`."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def ler_series_horarias(
        self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp
    ) -> pd.DataFrame:
        bruto = self._con.execute(
            _SQL, [sensor_id, inicio.to_pydatetime(), fim.to_pydatetime()]
        ).df()
        if bruto.empty:
            raise ValueError(f"sem leituras de {sensor_id} em [{inicio}, {fim})")
        bruto.loc[bruto["n"] < MINUTOS_POR_HORA, "kwh"] = float("nan")
        largo = bruto.pivot(index="hora", columns="equipamento_id", values="kwh")
        largo.index = pd.DatetimeIndex(largo.index)
        largo.columns.name = None
        return reindexar(largo.sort_index(), "1h", inicio, fim)
