"""Tabela de tarifa (Neoenergia PE, B3) e preco R$/kWh por timestamp e modalidade."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

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

# Horarios da tarifa branca conforme docs/m1_premissas.md (secao 1): ponta 18:00-20:59,
# intermediario 16:00-17:59, resto fora de ponta (pagina atual da Neoenergia PE).
# A hora 21:00 nao esta confirmada: a materia de 2018 e a regra ANEEL indicam intermediario
# apos a ponta; a pagina atual indica fora de ponta. Padrao fora de ponta, com chave
# `hora_21_intermediaria` em `Tarifas`.
HORAS_PONTA: range = range(18, 21)
HORAS_INTERMEDIARIO: range = range(16, 18)
HORA_21 = 21

# Feriados nacionais da lista de docs/m1_premissas.md (REN 1.000/2021, art. 2, via resumo de
# busca): 8 fixos + terca de carnaval, sexta-feira da Paixao e Corpus Christi (moveis).
# 20/nov (Consciencia Negra) NAO esta na lista e nao e modelado. A biblioteca `holidays`
# inclui 20/nov, vesperas, quarta de cinzas e facultativos, entao nao bate com a lista.
FERIADOS_FIXOS: tuple[tuple[int, int], ...] = (
    (1, 1),
    (4, 21),
    (5, 1),
    (9, 7),
    (10, 12),
    (11, 2),
    (11, 15),
    (12, 25),
)


def feriados_nacionais(ano: int) -> frozenset[date]:
    """Os 11 feriados nacionais da lista de docs/m1_premissas.md para o ano."""
    pascoa = easter(ano)
    moveis = {
        pascoa - timedelta(days=47),  # terca de carnaval
        pascoa - timedelta(days=2),  # sexta-feira da Paixao
        pascoa + timedelta(days=60),  # Corpus Christi
    }
    fixos = {date(ano, mes, dia) for mes, dia in FERIADOS_FIXOS}
    return frozenset(fixos | moveis)


def faixa_branca(indice: pd.DatetimeIndex, hora_21_intermediaria: bool = False) -> np.ndarray:
    """Posto horario da tarifa branca para cada timestamp (array de str).

    Fins de semana e feriados nacionais: fora de ponta o dia todo.
    """
    dias = indice.normalize()
    feriados = pd.DatetimeIndex(
        sorted(f for ano in dias.year.unique() for f in feriados_nacionais(int(ano)))
    )
    horas = indice.hour.to_numpy()
    util = (indice.dayofweek.to_numpy() < 5) & ~np.asarray(dias.isin(feriados))
    intermediario = list(HORAS_INTERMEDIARIO) + ([HORA_21] if hora_21_intermediaria else [])
    faixas = np.full(len(indice), FORA_PONTA, dtype=object)
    faixas[util & np.isin(horas, intermediario)] = INTERMEDIARIO
    faixas[util & np.isin(horas, list(HORAS_PONTA))] = PONTA
    return faixas


def _positivo_finito(valor: float, nome: str, minimo: float) -> None:
    if not math.isfinite(valor) or valor < minimo:
        raise ValueError(f"{nome} deve ser finito e >= {minimo}, veio {valor!r}")


@dataclass(frozen=True)
class Tarifas:
    """Precos R$/kWh por (modalidade, posto), carregados do CSV derivado do doc de regulacao.

    `precos_tabela` guarda a tarifa base (sem tributos e sem bandeira). `bandeira_rs_kwh` e
    `gross_up` sao opcionais e vazios por padrao: o preco usado nos calculos e
    `(base + bandeira) * gross_up`. O gross_up e multiplicativo (ICMS e PIS/Cofins "por dentro",
    ex.: 1 / (1 - aliquota total)); a bandeira entra como adicional uniforme por kWh, o que e
    uma hipotese (docs/m1_premissas.md, secao 3: incidencia por posto nao confirmada).
    """

    precos_tabela: dict[tuple[str, str], float]
    hora_21_intermediaria: bool = False
    gross_up: float | None = None
    bandeira_rs_kwh: float | None = None
    vigencia: tuple[date, date] | None = None

    def __post_init__(self) -> None:
        if self.gross_up is not None:
            _positivo_finito(self.gross_up, "gross_up", 1.0)
        if self.bandeira_rs_kwh is not None:
            _positivo_finito(self.bandeira_rs_kwh, "bandeira_rs_kwh", 0.0)

    @classmethod
    def carregar(
        cls,
        caminho: Path = CSV_PADRAO,
        referencia: date | None = None,
        hora_21_intermediaria: bool = False,
        gross_up: float | None = None,
        bandeira_rs_kwh: float | None = None,
    ) -> Tarifas:
        """Carrega a tabela vigente em `referencia`.

        A chave (modalidade, posto) deve ser unica por vigencia (erro caso contrario). Sem
        `referencia`, a tabela so pode ter uma vigencia; com mais de uma, e obrigatoria.
        """
        tabela = pd.read_csv(caminho, dtype={"modalidade": str, "posto": str})
        tabela["vigencia_inicio"] = pd.to_datetime(tabela["vigencia_inicio"])
        tabela["vigencia_fim"] = pd.to_datetime(tabela["vigencia_fim"])
        chave = ["modalidade", "posto", "vigencia_inicio"]
        repetidas = tabela[tabela.duplicated(chave, keep=False)]
        if not repetidas.empty:
            pares = sorted({(str(m), str(p)) for m, p in zip(repetidas["modalidade"], repetidas["posto"], strict=True)})
            raise ValueError(f"chave (modalidade, posto) repetida na mesma vigencia: {pares}")
        if referencia is None:
            vigencias = tabela[["vigencia_inicio", "vigencia_fim"]].drop_duplicates()
            if len(vigencias) > 1:
                raise ValueError("tabela com mais de uma vigencia: informe `referencia`")
            vigente = tabela
        else:
            ref = pd.Timestamp(referencia)
            vigente = tabela[(tabela["vigencia_inicio"] <= ref) & (ref <= tabela["vigencia_fim"])]
            if vigente.empty:
                raise ValueError(f"nenhuma tarifa vigente em {referencia}")
        inicio = pd.Timestamp(vigente["vigencia_inicio"].iloc[0]).date()
        fim = pd.Timestamp(vigente["vigencia_fim"].iloc[0]).date()
        precos = {
            (mod, posto): valor
            for mod, posto, valor in zip(
                vigente["modalidade"].astype(str),
                vigente["posto"].astype(str),
                vigente["tarifa_rs_kwh"].astype(float),
                strict=True,
            )
        }
        return cls(precos, hora_21_intermediaria, gross_up, bandeira_rs_kwh, (inicio, fim))

    def preco_posto(self, modalidade: str, posto: str) -> float:
        """Preco R$/kWh: (tarifa base + bandeira) x gross_up; so a base quando ambos vazios."""
        try:
            base = self.precos_tabela[(modalidade, posto)]
        except KeyError as erro:
            raise KeyError(f"sem preco para modalidade={modalidade!r} posto={posto!r}") from erro
        return (base + (self.bandeira_rs_kwh or 0.0)) * (self.gross_up or 1.0)

    def descricao_valores(self) -> str:
        """Texto para o relatorio: o que os valores incluem."""
        if self.gross_up is None and self.bandeira_rs_kwh is None:
            return "SEM tributos e SEM bandeira (tarifa base homologada)"
        partes = []
        partes.append(
            "sem bandeira"
            if self.bandeira_rs_kwh is None
            else f"com bandeira de R$ {self.bandeira_rs_kwh:.5f}/kWh somada a todos os postos (hipotese)"
        )
        partes.append(
            "sem tributos"
            if self.gross_up is None
            else f"com gross-up multiplicativo de {self.gross_up:.4f} (tributos, informado, nao conferido)"
        )
        return ", ".join(partes)

    def faixas(self, indice: pd.DatetimeIndex, modalidade: str) -> np.ndarray:
        """Faixa de cada timestamp: 'unico' na convencional, posto horario na branca."""
        if modalidade == CONVENCIONAL:
            return np.full(len(indice), FAIXA_UNICA, dtype=object)
        if modalidade == BRANCA:
            return faixa_branca(indice, self.hora_21_intermediaria)
        raise ValueError(f"modalidade desconhecida: {modalidade!r}")

    def precos(self, indice: pd.DatetimeIndex, modalidade: str) -> np.ndarray:
        """Preco R$/kWh para cada timestamp do indice."""
        faixas = self.faixas(indice, modalidade)
        por_faixa = {f: self.preco_posto(modalidade, f) for f in np.unique(faixas)}
        return np.array([por_faixa[f] for f in faixas], dtype=float)

    def preco_em(self, ts: pd.Timestamp, modalidade: str) -> float:
        """Preco R$/kWh em um timestamp e modalidade."""
        return float(self.precos(pd.DatetimeIndex([ts]), modalidade)[0])
