"""Top-N equipamentos por custo mensal."""

from __future__ import annotations

import pandas as pd


def pct_ausente_por_equipamento(leituras: pd.DataFrame) -> pd.Series[float]:
    """Percentual (0-100) de pontos ausentes por equipamento, a partir de `ausente`."""
    return leituras.groupby("equipamento_id")["ausente"].mean().astype(float) * 100.0


def top_n(custos: pd.DataFrame, pct_ausente: pd.Series[float], n: int = 5) -> pd.DataFrame:
    """Soma kWh e custo por equipamento (todas as faixas) e devolve os N maiores por custo.

    Colunas: equipamento_id, kwh, custo_rs, pct_ausente (0-100; custo e piso quando > 0).
    """
    por_equipamento = custos.groupby("equipamento_id", as_index=False)[["kwh", "custo_rs"]].sum()
    por_equipamento["pct_ausente"] = (
        por_equipamento["equipamento_id"].map(pct_ausente).astype(float)
    )
    ordenado = por_equipamento.sort_values(
        ["custo_rs", "equipamento_id"], ascending=[False, True]
    )
    return ordenado.head(n).reset_index(drop=True)
