"""Entidades do dominio. Sem I/O e sem framework."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from datetime import datetime


class ErroDominio(ValueError):
    """Violacao de uma regra de dominio."""


@dataclass(frozen=True)
class Empresa:
    id: str
    nome: str


@dataclass(frozen=True)
class Unidade:
    id: str
    empresa_id: str
    nome: str


@dataclass(frozen=True)
class Sensor:
    """Dispositivo de medicao. `id` e tambem o `device_id` das chaves de comando."""

    id: str
    empresa_id: str
    unidade_id: str
    nome: str


@dataclass(frozen=True)
class Equipamento:
    """Carga monitorada. `nome` e o `equipamento_id` gravado em `leitura`."""

    id: str
    empresa_id: str
    sensor_id: str
    nome: str
    critico: bool = False


@dataclass(frozen=True)
class Leitura:
    sensor_id: str
    equipamento_nome: str
    ts: datetime
    potencia_w: float | None
    tensao_v: float | None
    kwh: float | None
    ausente: bool = False


_CRON = re.compile(r"^\s*\S+(\s+\S+){4}\s*$")


@dataclass(frozen=True)
class RegraDesligamento:
    id: str
    empresa_id: str
    equipamento_id: str
    cron: str
    ativo: bool
    autorizado_por: str
    criado_em: datetime

    def __post_init__(self) -> None:
        if not _CRON.match(self.cron):
            raise ErroDominio(f"cron deve ter 5 campos, veio {self.cron!r}")
        if not self.autorizado_por.strip():
            raise ErroDominio("regra exige autorizado_por")


class TipoEvento(enum.StrEnum):
    DESLIGAMENTO_EXECUTADO = "desligamento_executado"
    RELIGAMENTO_EXECUTADO = "religamento_executado"
    COMANDO_REJEITADO = "comando_rejeitado"
    QUEDA_ENERGIA = "queda_energia"
    FALHA_CONEXAO = "falha_conexao"


@dataclass(frozen=True)
class Evento:
    id: str
    ts: datetime
    tipo: TipoEvento
    empresa_id: str
    sensor_id: str | None
    equipamento_id: str | None
    origem: str
    regra_id: str | None
    autorizado_por: str | None
    payload: dict[str, str] = field(default_factory=dict)
