"""Portas (interfaces) que a infraestrutura implementa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mapen_plataforma.domain.comando import Acao, EstadoRele
from mapen_plataforma.domain.entidades import (
    Empresa,
    Equipamento,
    Evento,
    Leitura,
    RegraDesligamento,
    Sensor,
    Unidade,
)


class Relogio(Protocol):
    def agora(self) -> datetime: ...


class GeradorId(Protocol):
    def novo(self) -> str: ...


class EmpresaRepo(Protocol):
    def obter(self, empresa_id: str) -> Empresa | None: ...


class UnidadeRepo(Protocol):
    def adicionar(self, unidade: Unidade) -> None: ...
    def listar(self, empresa_id: str) -> list[Unidade]: ...
    def obter(self, empresa_id: str, unidade_id: str) -> Unidade | None: ...


class SensorRepo(Protocol):
    def adicionar(self, sensor: Sensor) -> None: ...
    def listar(self, empresa_id: str) -> list[Sensor]: ...
    def obter(self, empresa_id: str, sensor_id: str) -> Sensor | None: ...


class EquipamentoRepo(Protocol):
    def adicionar(self, equipamento: Equipamento) -> None: ...
    def listar(self, empresa_id: str) -> list[Equipamento]: ...
    def obter(self, empresa_id: str, equipamento_id: str) -> Equipamento | None: ...


class RegraRepo(Protocol):
    def adicionar(self, regra: RegraDesligamento) -> None: ...
    def listar(self, empresa_id: str) -> list[RegraDesligamento]: ...
    def definir_ativo(self, empresa_id: str, regra_id: str, ativo: bool) -> bool: ...


class EventoRepo(Protocol):
    def adicionar(self, evento: Evento) -> None: ...
    def listar(self, empresa_id: str, limite: int) -> list[Evento]: ...


class NonceStore(Protocol):
    def registrar(self, device_id: str, nonce: str) -> bool:
        """Grava o nonce. False se ja existia (repeticao). Atomico."""
        ...


class ChavesDispositivo(Protocol):
    def chave(self, device_id: str) -> bytes | None: ...


class Atuador(Protocol):
    """Aciona o rele. Sem hardware ainda: a unica implementacao e simulada."""

    def aplicar(self, device_id: str, equipamento_id: str, acao: Acao) -> None: ...
    def estado(self, device_id: str, equipamento_id: str) -> EstadoRele: ...


class LeituraRepo(Protocol):
    """Porta de ingestao e consulta de leituras (a fonte pode ser MQTT, HTTP ou dado de demo)."""

    def adicionar(self, leituras: list[Leitura]) -> int:
        """Grava sem duplicar (sensor, equipamento, ts) ja existentes. Devolve novas linhas."""
        ...

    def ultimo_ts(self, sensor_id: str) -> datetime | None: ...

    def consumo_por_equipamento(
        self, sensor_id: str, inicio: datetime, fim: datetime
    ) -> list[ConsumoEquipamento]: ...

    def potencia_em(self, sensor_id: str, ts: datetime) -> float: ...


@dataclass(frozen=True)
class ConsumoEquipamento:
    equipamento_nome: str
    kwh: float


@dataclass(frozen=True)
class CustoLinha:
    equipamento_nome: str
    faixa: str
    kwh: float
    custo_rs: float


@dataclass(frozen=True)
class RankingLinha:
    equipamento_nome: str
    kwh: float
    custo_rs: float
    pct_ausente: float


class CalculadoraCusto(Protocol):
    """Custo e ranking por tarifa; a implementacao reusa o pacote M1."""

    def custo_por_faixa(
        self, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str
    ) -> list[CustoLinha]: ...

    def ranking(
        self, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str, n: int
    ) -> list[RankingLinha]: ...

