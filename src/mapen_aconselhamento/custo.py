"""Custo por equipamento e faixa horaria."""

from __future__ import annotations

import pandas as pd

from mapen_aconselhamento.tarifa import Tarifas

COLUNAS_CUSTO: list[str] = ["equipamento_id", "faixa", "kwh", "custo_rs"]


def custo_por_faixa(leituras: pd.DataFrame, tarifas: Tarifas, modalidade: str) -> pd.DataFrame:
    """Custo (R$) por equipamento e faixa.

    `leituras` tem colunas `ts`, `equipamento_id`, `kwh` (NULL nas lacunas). Pontos ausentes
    nao entram na soma (nao ha interpolacao): o custo e um piso quando ha lacunas.
    """
    if leituras.empty:
        return pd.DataFrame(columns=COLUNAS_CUSTO)
    ts = pd.DatetimeIndex(pd.to_datetime(leituras["ts"]))
    base = pd.DataFrame(
        {
            "equipamento_id": leituras["equipamento_id"].to_numpy(),
            "faixa": tarifas.faixas(ts, modalidade),
            "kwh": leituras["kwh"].to_numpy(dtype=float),
            "preco": tarifas.precos(ts, modalidade),
        }
    )
    base["custo_rs"] = base["kwh"] * base["preco"]
    agregado = (
        base.groupby(["equipamento_id", "faixa"], as_index=False)[["kwh", "custo_rs"]]
        .sum(min_count=1)
        .fillna(0.0)
    )
    return agregado[COLUNAS_CUSTO]


def custo_total(custos: pd.DataFrame) -> float:
    return float(custos["custo_rs"].sum())
