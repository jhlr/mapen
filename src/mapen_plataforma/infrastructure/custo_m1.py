"""Adaptador que reusa o pacote M1 (custo por faixa e ranking) sobre a tabela `leitura`."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from mapen_aconselhamento.custo import custo_por_faixa
from mapen_aconselhamento.ingest import ler_leituras
from mapen_aconselhamento.ranking import pct_ausente_por_equipamento, top_n
from mapen_aconselhamento.tarifa import Tarifas
from mapen_plataforma.application.portas import CustoLinha, RankingLinha
from mapen_plataforma.domain.tempo import para_local_ingenuo
from mapen_plataforma.infrastructure.banco import BancoDuckDB


class CalculadoraM1:
    def __init__(self, banco: BancoDuckDB, tarifas: Tarifas | None = None) -> None:
        self._banco = banco
        self._tarifas = tarifas or Tarifas.carregar()

    def _leituras(self, sensor_id: str, inicio: datetime, fim: datetime) -> pd.DataFrame:
        with self._banco.trava:
            return ler_leituras(
                self._banco.conexao,
                sensor_id,
                pd.Timestamp(para_local_ingenuo(inicio, "inicio")),
                pd.Timestamp(para_local_ingenuo(fim, "fim")),
            )

    def faixas(self, instantes: list[datetime], modalidade: str) -> list[str]:
        """Faixa tarifaria de cada instante, pela mesma `Tarifas.faixas` do custo."""
        if not instantes:
            return []
        indice = pd.DatetimeIndex([para_local_ingenuo(t, "hora") for t in instantes])
        return [str(f) for f in self._tarifas.faixas(indice, modalidade)]

    def custo_por_faixa(
        self, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str
    ) -> list[CustoLinha]:
        leituras = self._leituras(sensor_id, inicio, fim)
        custos = custo_por_faixa(leituras, self._tarifas, modalidade)
        return [
            CustoLinha(eq, faixa, kwh, rs)
            for eq, faixa, kwh, rs in zip(
                custos["equipamento_id"].astype(str),
                custos["faixa"].astype(str),
                custos["kwh"].astype(float),
                custos["custo_rs"].astype(float),
                strict=True,
            )
        ]

    def ranking(
        self, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str, n: int
    ) -> list[RankingLinha]:
        leituras = self._leituras(sensor_id, inicio, fim)
        custos = custo_por_faixa(leituras, self._tarifas, modalidade)
        if custos.empty:
            return []
        topo = top_n(custos, pct_ausente_por_equipamento(leituras), n)
        return [
            RankingLinha(eq, kwh, rs, ausente)
            for eq, kwh, rs, ausente in zip(
                topo["equipamento_id"].astype(str),
                topo["kwh"].astype(float),
                topo["custo_rs"].astype(float),
                topo["pct_ausente"].astype(float),
                strict=True,
            )
        ]
