"""Top-N equipamentos por custo mensal."""

from __future__ import annotations

import pandas as pd


def top_n(custos: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Soma kWh e custo por equipamento (todas as faixas) e devolve os N maiores por custo."""
    por_equipamento = custos.groupby("equipamento_id", as_index=False)[["kwh", "custo_rs"]].sum()
    ordenado = por_equipamento.sort_values(
        ["custo_rs", "equipamento_id"], ascending=[False, True]
    )
    return ordenado.head(n).reset_index(drop=True)
