"""Regras por equipamento: flexibilidade, criticidade e fracao movivel por cenario."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase

BAIXA = "baixa"
CENTRAL = "central"
ALTA = "alta"
CENARIOS: tuple[str, str, str] = (BAIXA, CENTRAL, ALTA)


@dataclass(frozen=True)
class Regra:
    classe: str
    flexivel: bool
    critico: bool
    fracao_movivel: float
    faixa_fracao: tuple[float, float] | None = None

    def fracao(self, cenario: str) -> float:
        """Fracao movivel do cenario: central, ou baixa/alta da faixa sourced (central se sem faixa)."""
        if cenario == CENTRAL or self.faixa_fracao is None:
            return self.fracao_movivel
        if cenario == BAIXA:
            return self.faixa_fracao[0]
        if cenario == ALTA:
            return self.faixa_fracao[1]
        raise ValueError(f"cenario desconhecido: {cenario!r}")


@dataclass(frozen=True)
class ConfigEquipamentos:
    regras: tuple[tuple[str, Regra], ...]
    padrao: Regra

    @classmethod
    def de_dict(cls, bruto: object) -> ConfigEquipamentos:
        """Monta a config a partir do documento ja lido (mapa com `equipamentos` e `padrao`)."""
        if not isinstance(bruto, Mapping):
            raise ValueError("config de equipamentos deve ser um mapa")
        entradas = bruto["equipamentos"]
        if not isinstance(entradas, list):
            raise ValueError("`equipamentos` deve ser uma lista")
        regras = tuple((str(e["padrao"]), _regra(e)) for e in entradas)
        return cls(regras, _regra(bruto.get("padrao", {})))

    def encontrar(self, equipamento_id: str) -> Regra | None:
        """Regra que casa explicitamente com o equipamento; None se so o padrao se aplicaria."""
        for padrao, regra in self.regras:
            if fnmatchcase(equipamento_id, padrao):
                return regra
        return None

    def para(self, equipamento_id: str) -> Regra:
        for padrao, regra in self.regras:
            if fnmatchcase(equipamento_id, padrao):
                return regra
        return self.padrao


def _fracao(entrada: Mapping[str, object], chave: str, equipamento: str) -> float | None:
    """Le uma fracao movivel da config; valida finita e 0 < f <= 1. None se ausente."""
    if chave not in entrada:
        return None
    try:
        valor = float(str(entrada[chave]))
    except ValueError:
        valor = math.nan
    if not math.isfinite(valor) or not 0.0 < valor <= 1.0:
        raise ValueError(
            f"{chave} de {equipamento!r} deve ser finita e 0 < f <= 1, veio {entrada[chave]!r}"
        )
    return valor


def _regra(entrada: Mapping[str, object]) -> Regra:
    nome = str(entrada.get("padrao", "padrao"))
    flexivel = bool(entrada.get("flexivel", False))
    central = _fracao(entrada, "fracao_movivel", nome)
    baixa = _fracao(entrada, "fracao_movivel_baixa", nome)
    alta = _fracao(entrada, "fracao_movivel_alta", nome)
    if flexivel and central is None:
        raise ValueError(f"regra flexivel {nome!r} exige fracao_movivel")
    if central is None:
        central = 0.0
    faixa: tuple[float, float] | None = None
    if baixa is not None or alta is not None:
        faixa = (baixa if baixa is not None else central, alta if alta is not None else central)
        if not faixa[0] <= central <= faixa[1]:
            raise ValueError(f"regra {nome!r}: exige baixa <= central <= alta, veio {faixa[0]}, {central}, {faixa[1]}")
    return Regra(
        classe=str(entrada.get("classe", "desconhecida")),
        flexivel=flexivel,
        critico=bool(entrada.get("critico", False)),
        fracao_movivel=central,
        faixa_fracao=faixa,
    )
