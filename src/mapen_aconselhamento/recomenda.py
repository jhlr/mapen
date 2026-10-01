"""Recomendacao de mover carga flexivel entre faixas horarias."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

import pandas as pd
import yaml

from mapen_aconselhamento.tarifa import BRANCA, FAIXAS_BRANCA, FORA_PONTA, RAIZ, Tarifas

YAML_PADRAO: Path = RAIZ / "config" / "equipamentos.yaml"


@dataclass(frozen=True)
class Regra:
    classe: str
    flexivel: bool
    critico: bool
    fracao_movivel: float


@dataclass(frozen=True)
class ConfigEquipamentos:
    regras: tuple[tuple[str, Regra], ...]
    padrao: Regra

    @classmethod
    def carregar(cls, caminho: Path = YAML_PADRAO) -> ConfigEquipamentos:
        bruto = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        regras = tuple((str(e["padrao"]), _regra(e)) for e in bruto["equipamentos"])
        return cls(regras, _regra(bruto.get("padrao", {})))

    def para(self, equipamento_id: str) -> Regra:
        for padrao, regra in self.regras:
            if fnmatchcase(equipamento_id, padrao):
                return regra
        return self.padrao


def _regra(entrada: dict[str, object]) -> Regra:
    return Regra(
        classe=str(entrada.get("classe", "desconhecida")),
        flexivel=bool(entrada.get("flexivel", False)),
        critico=bool(entrada.get("critico", False)),
        fracao_movivel=float(str(entrada.get("fracao_movivel", 0.0))),
    )


@dataclass(frozen=True)
class Recomendacao:
    equipamento_id: str
    faixa_origem: str
    faixa_destino: str
    kwh_movido: float
    economia_rs: float


def recomendar(
    custos_branca: pd.DataFrame,
    tarifas: Tarifas,
    config: ConfigEquipamentos,
    faixa_destino: str = FORA_PONTA,
) -> list[Recomendacao]:
    """Economia de mover kWh da faixa A para a faixa B = kWh x (preco A - preco B).

    So considera equipamento marcado `flexivel` (e nao `critico`) em config. O kWh movido e
    kWh da faixa A x `fracao_movivel` (hipotese de cenario da config). Ordenado por economia.
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
        movido = kwh * regra.fracao_movivel
        if movido <= 0:
            continue
        saida.append(Recomendacao(equipamento, faixa, faixa_destino, movido, movido * diferenca))
    return sorted(saida, key=lambda r: r.economia_rs, reverse=True)
