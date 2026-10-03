"""Recomendacao de mover carga flexivel entre faixas horarias."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mapen_aconselhamento.domain.equipamentos import CENTRAL, ConfigEquipamentos
from mapen_aconselhamento.domain.tarifa import BRANCA, FAIXAS_BRANCA, FORA_PONTA, Tarifas


@dataclass(frozen=True)
class Recomendacao:
    equipamento_id: str
    faixa_origem: str
    faixa_destino: str
    kwh_movido: float
    economia_rs: float
    fracao_movivel: float


def recomendar(
    custos_branca: pd.DataFrame,
    tarifas: Tarifas,
    config: ConfigEquipamentos,
    faixa_destino: str = FORA_PONTA,
    cenario: str = CENTRAL,
) -> list[Recomendacao]:
    """Economia de mover kWh da faixa A para a faixa B = kWh x (preco A - preco B).

    So considera equipamento marcado `flexivel` (e nao `critico`) em config. O kWh movido e
    kWh da faixa A x fracao movivel do `cenario` (baixa/central/alta; hipotese da config, nao
    medicao). Ordenado por economia.
    """
    preco_destino = tarifas.preco_posto(BRANCA, faixa_destino)
    saida: list[Recomendacao] = []
    linhas = zip(
        custos_branca["equipamento_id"].astype(str),
        custos_branca["faixa"].astype(str),
        custos_branca["kwh"].astype(float),
        strict=True,
    )
    for equipamento, faixa, kwh in linhas:
        regra = config.para(equipamento)
        if not regra.flexivel or regra.critico or faixa not in FAIXAS_BRANCA:
            continue
        diferenca = tarifas.preco_posto(BRANCA, faixa) - preco_destino
        if diferenca <= 0:
            continue
        fracao = regra.fracao(cenario)
        movido = kwh * fracao
        if movido <= 0:
            continue
        saida.append(Recomendacao(equipamento, faixa, faixa_destino, movido, movido * diferenca, fracao))
    return sorted(saida, key=lambda r: r.economia_rs, reverse=True)
