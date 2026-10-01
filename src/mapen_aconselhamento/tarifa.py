"""Tabela de tarifa (Neoenergia PE, B3) e preco R$/kWh por timestamp e modalidade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ: Path = Path(__file__).resolve().parents[2]
CSV_PADRAO: Path = RAIZ / "data" / "tarifas" / "neoenergia_pe.csv"

CONVENCIONAL = "convencional"
BRANCA = "branca"
MODALIDADES: tuple[str, str] = (CONVENCIONAL, BRANCA)
FAIXA_UNICA = "unico"
PONTA = "ponta"
INTERMEDIARIO = "intermediario"
FORA_PONTA = "fora_ponta"
FAIXAS_BRANCA: tuple[str, str, str] = (PONTA, INTERMEDIARIO, FORA_PONTA)

# Horarios da tarifa branca conforme docs/regulacao/tarifas_neoenergia_pe.md:
# ponta 18:00-20:59, intermediario 16:00-17:59, resto fora de ponta. A janela
# intermediaria apos a ponta (21h) nao foi confirmada para PE: tratada como fora de ponta.
# Fins de semana: sempre fora de ponta. Feriados nacionais nao estao modelados.
HORAS_PONTA: range = range(18, 21)
HORAS_INTERMEDIARIO: range = range(16, 18)


def faixa_branca(indice: pd.DatetimeIndex) -> np.ndarray:
    """Posto horario da tarifa branca para cada timestamp (array de str)."""
    horas = indice.hour.to_numpy()
    util = indice.dayofweek.to_numpy() < 5
    faixas = np.full(len(indice), FORA_PONTA, dtype=object)
    faixas[util & np.isin(horas, list(HORAS_INTERMEDIARIO))] = INTERMEDIARIO
    faixas[util & np.isin(horas, list(HORAS_PONTA))] = PONTA
    return faixas


@dataclass(frozen=True)
class Tarifas:
    """Precos R$/kWh por (modalidade, posto), carregados do CSV derivado do doc de regulacao."""

    precos_tabela: dict[tuple[str, str], float]

    @classmethod
    def carregar(cls, caminho: Path = CSV_PADRAO) -> Tarifas:
        tabela = pd.read_csv(caminho, dtype={"modalidade": str, "posto": str})
        precos = {
            (mod, posto): valor
            for mod, posto, valor in zip(
                tabela["modalidade"].astype(str),
                tabela["posto"].astype(str),
                tabela["tarifa_rs_kwh"].astype(float),
                strict=True,
            )
        }
        return cls(precos)

    def preco_posto(self, modalidade: str, posto: str) -> float:
        try:
            return self.precos_tabela[(modalidade, posto)]
        except KeyError as erro:
            raise KeyError(f"sem preco para modalidade={modalidade!r} posto={posto!r}") from erro

    def faixas(self, indice: pd.DatetimeIndex, modalidade: str) -> np.ndarray:
        """Faixa de cada timestamp: 'unico' na convencional, posto horario na branca."""
        if modalidade == CONVENCIONAL:
            return np.full(len(indice), FAIXA_UNICA, dtype=object)
        if modalidade == BRANCA:
            return faixa_branca(indice)
        raise ValueError(f"modalidade desconhecida: {modalidade!r}")

    def precos(self, indice: pd.DatetimeIndex, modalidade: str) -> np.ndarray:
        """Preco R$/kWh para cada timestamp do indice."""
        faixas = self.faixas(indice, modalidade)
        por_faixa = {f: self.preco_posto(modalidade, f) for f in np.unique(faixas)}
        return np.array([por_faixa[f] for f in faixas], dtype=float)

    def preco_em(self, ts: pd.Timestamp, modalidade: str) -> float:
        """Preco R$/kWh em um timestamp e modalidade."""
        return float(self.precos(pd.DatetimeIndex([ts]), modalidade)[0])
