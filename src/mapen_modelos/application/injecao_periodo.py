"""Injecao sintetica por periodo reservado, compartilhada pelos benchmarks (mesma semente, mesmos eventos).

Escala = P95 do equipamento nas horas anteriores a `inicio` presentes em `series` (os benchmarks
leem so o aquecimento antes de `inicio`), como no benchmark sintetico original.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mapen_modelos.domain.injecao import EventoInjetado, injetar_anomalias


def injetar_no_periodo(
    series: pd.DataFrame, equipamentos: list[str], inicio: pd.Timestamp, semente: int, por_tipo: int
) -> tuple[pd.DataFrame, dict[str, list[EventoInjetado]]]:
    """Copia de `series` com `por_tipo` eventos de cada tipo por equipamento em [inicio, fim)."""
    rng = np.random.default_rng(semente)
    injetada = series.copy()
    eventos_por_eq: dict[str, list[EventoInjetado]] = {}
    for eq in equipamentos:
        janela = pd.DatetimeIndex(injetada.index) >= inicio
        sub = injetada.loc[janela, eq]
        p95 = float(series.loc[series.index < inicio, eq].quantile(0.95))
        nova, eventos = injetar_anomalias(sub, p95, rng, por_tipo)
        injetada.loc[janela, eq] = nova
        eventos_por_eq[eq] = eventos
    return injetada, eventos_por_eq
