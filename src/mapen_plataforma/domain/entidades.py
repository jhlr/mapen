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
    critico: bool


@dataclass(frozen=True)
class Leitura:
    sensor_id: str
    equipamento_nome: str
    ts: datetime
    potencia_w: float | None
    tensao_v: float | None
    kwh: float | None
    ausente: bool = False

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None:
            raise ErroDominio("ts da leitura deve ter fuso horario")


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
    COMANDO_RECEBIDO = "comando_recebido"
    COMANDO_REJEITADO = "comando_rejeitado"
    CONFIGURACAO_ALTERADA = "configuracao_alterada"
    ULTIMO_SUSPIRO = "ultimo_suspiro"
    QUEDA_ENERGIA = "queda_energia"
    FALHA_CONEXAO = "falha_conexao"


# Eventos que o proprio dispositivo registra no seu relogio (RTC) e envia depois; os demais nascem na plataforma.
TIPOS_DE_DISPOSITIVO: frozenset[TipoEvento] = frozenset(
    {TipoEvento.ULTIMO_SUSPIRO, TipoEvento.QUEDA_ENERGIA, TipoEvento.FALHA_CONEXAO}
)


@dataclass(frozen=True)
class EventoDispositivo:
    """Evento medido pelo RTC do dispositivo. `fim` e `duracao_s` ficam ausentes quando o RTC nao sobreviveu."""

    tipo: TipoEvento
    inicio: datetime
    fim: datetime | None = None
    duracao_s: float | None = None
    bateria_esgotada: bool = False

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_DE_DISPOSITIVO:
            raise ErroDominio(f"tipo {self.tipo.value!r} nao e um evento de dispositivo")
        if self.inicio.tzinfo is None or (self.fim is not None and self.fim.tzinfo is None):
            raise ErroDominio("instantes do evento devem ter fuso horario")
        if self.fim is not None and self.fim < self.inicio:
            raise ErroDominio("fim do evento anterior ao inicio")
        if self.duracao_s is not None and self.duracao_s < 0:
            raise ErroDominio("duracao do evento negativa")
        if self.tipo is TipoEvento.ULTIMO_SUSPIRO and (self.fim is not None or self.duracao_s is not None):
            raise ErroDominio("ultimo_suspiro marca so o inicio da queda")


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
