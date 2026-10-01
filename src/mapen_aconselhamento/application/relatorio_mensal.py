"""Caso de uso: relatorio de custo e recomendacoes de um predio em um mes."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mapen_aconselhamento.application.portas import RepositorioLeituras
from mapen_aconselhamento.domain.custo import custo_por_faixa, custo_total
from mapen_aconselhamento.domain.equipamentos import ALTA, BAIXA, CENTRAL, ConfigEquipamentos
from mapen_aconselhamento.domain.ranking import pct_ausente_por_equipamento, top_n
from mapen_aconselhamento.domain.recomendacao import Recomendacao, recomendar
from mapen_aconselhamento.domain.tarifa import BRANCA, CONVENCIONAL, Tarifas

FONTE_DADOS_PADRAO = "dataset publico (ver docs/datasets_publicos.md)"


@dataclass(frozen=True)
class LinhaRanking:
    equipamento_id: str
    kwh: float
    custo_convencional_rs: float
    custo_branca_rs: float
    flexivel: bool
    pct_ausente: float


@dataclass(frozen=True)
class RelatorioMensal:
    sensor_id: str
    mes: str
    n: int
    fonte_dados: str
    tarifas: Tarifas
    pontos: int
    ausentes: int
    duplicados: tuple[int, str] | None
    custo_convencional_rs: float
    custo_branca_rs: float
    ranking: tuple[LinhaRanking, ...]
    recomendacoes: dict[str, tuple[Recomendacao, ...]]

    @property
    def pct_ausente(self) -> float:
        return 100.0 * self.ausentes / self.pontos

    def economia_total(self, cenario: str) -> float:
        return sum(r.economia_rs for r in self.recomendacoes[cenario])

    def fracoes(self, cenario: str) -> list[float]:
        return [r.fracao_movivel for r in self.recomendacoes[cenario]]


class GerarRelatorioMensal:
    def __init__(self, leituras: RepositorioLeituras) -> None:
        self._leituras = leituras

    def executar(
        self,
        sensor_id: str,
        mes: str,
        tarifas: Tarifas,
        config: ConfigEquipamentos,
        n: int = 5,
        fonte_dados: str = FONTE_DADOS_PADRAO,
    ) -> RelatorioMensal:
        """Relatorio do predio `sensor_id` no mes `mes` (formato AAAA-MM)."""
        inicio = pd.Timestamp(f"{mes}-01")
        fim = inicio + pd.offsets.MonthBegin(1)
        leituras = self._leituras.ler_leituras(sensor_id, inicio, fim)
        if leituras.empty:
            raise ValueError(f"sem leituras para {sensor_id} em {mes}")

        conv = custo_por_faixa(leituras, tarifas, CONVENCIONAL)
        branca = custo_por_faixa(leituras, tarifas, BRANCA)
        rank_conv = top_n(conv, pct_ausente_por_equipamento(leituras), n)
        custo_branca = branca.groupby("equipamento_id")["custo_rs"].sum()
        ranking = tuple(
            LinhaRanking(
                equipamento_id=eq,
                kwh=kwh,
                custo_convencional_rs=custo,
                custo_branca_rs=float(custo_branca.get(eq, 0.0)),
                flexivel=config.para(eq).flexivel,
                pct_ausente=pct,
            )
            for eq, kwh, custo, pct in zip(
                rank_conv["equipamento_id"].astype(str),
                rank_conv["kwh"].astype(float),
                rank_conv["custo_rs"].astype(float),
                rank_conv["pct_ausente"].astype(float),
                strict=True,
            )
        )
        return RelatorioMensal(
            sensor_id=sensor_id,
            mes=mes,
            n=n,
            fonte_dados=fonte_dados,
            tarifas=tarifas,
            pontos=len(leituras),
            ausentes=int(leituras["ausente"].sum()),
            duplicados=self._leituras.ler_duplicados(sensor_id),
            custo_convencional_rs=custo_total(conv),
            custo_branca_rs=custo_total(branca),
            ranking=ranking,
            recomendacoes={
                c: tuple(recomendar(branca, tarifas, config, cenario=c)) for c in (BAIXA, CENTRAL, ALTA)
            },
        )
