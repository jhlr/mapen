"""Portas (interfaces) que a infraestrutura implementa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mapen_plataforma.domain.comando import Acao, ConfiguracaoSeguranca, EstadoRele
from mapen_plataforma.domain.credenciais import Principal
from mapen_plataforma.domain.entidades import (
    Empresa,
    Equipamento,
    Evento,
    Leitura,
    RegraDesligamento,
    Sensor,
    Unidade,
)
from mapen_plataforma.domain.resultados_m3 import AlertasM3, EconomiaM3, EstudoPrevisao, ResumoM3


class Relogio(Protocol):
    def agora(self) -> datetime: ...


class GeradorId(Protocol):
    def novo(self) -> str: ...


class EmpresaRepo(Protocol):
    def adicionar(self, empresa: Empresa) -> None: ...
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
    def obter(self, empresa_id: str, regra_id: str) -> RegraDesligamento | None: ...
    def definir_ativo(self, empresa_id: str, regra_id: str, ativo: bool) -> bool: ...


class EventoRepo(Protocol):
    def adicionar(self, evento: Evento) -> None: ...
    def listar(self, empresa_id: str, limite: int) -> list[Evento]: ...


class EventoUnicoRepo(Protocol):
    """Gravacao idempotente de eventos que o dispositivo reenvia ate ter confirmacao."""

    def adicionar_se_novo(self, evento: Evento) -> bool:
        """Grava so se o id ainda nao existe (reenvio do lote nao duplica). False se ja existia. Atomico."""
        ...


class NonceStore(Protocol):
    def registrar(self, device_id: str, nonce: str, expira_em: datetime) -> bool:
        """Grava o nonce. False se ja existia (repeticao). Atomico."""
        ...

    def podar(self, agora: datetime) -> int:
        """Apaga nonces cuja janela de uso ja acabou. Devolve quantos."""
        ...


@dataclass(frozen=True)
class CredencialDispositivo:
    device_id: str
    empresa_id: str
    token_hash: str
    sal: str


class CredenciaisEmpresaRepo(Protocol):
    def definir(self, empresa_id: str, principal: str, hash_chave: str) -> None:
        """Uma credencial por (empresa, principal): substitui a anterior."""
        ...

    def buscar(self, hash_chave: str) -> Principal | None: ...


class CredenciaisDispositivoRepo(Protocol):
    def definir(self, credencial: CredencialDispositivo) -> None: ...
    def obter(self, device_id: str) -> CredencialDispositivo | None: ...


class ConfiguracaoRepo(Protocol):
    def obter(self, empresa_id: str) -> ConfiguracaoSeguranca: ...
    def definir(self, empresa_id: str, config: ConfiguracaoSeguranca) -> None: ...


class ChavesDispositivo(Protocol):
    """Chave HMAC de assinatura de comandos de um dispositivo (None se nao provisionado)."""

    def chave(self, device_id: str) -> bytes | None: ...


class DerivadorChave(Protocol):
    """Deriva a chave de comando a partir do segredo mestre do servidor e do sal do dispositivo."""

    def derivar(self, device_id: str, sal: str) -> bytes: ...


class ErroAtuador(RuntimeError):
    """O rele nao confirmou o comando."""


class Atuador(Protocol):
    """Aciona o rele. Sem hardware ainda: a unica implementacao e simulada.

    Levanta `ErroAtuador` se o comando nao foi aplicado.
    """

    def aplicar(self, device_id: str, equipamento_id: str, acao: Acao) -> None: ...
    def estado(self, device_id: str, equipamento_id: str) -> EstadoRele: ...


class LeituraRepo(Protocol):
    """Porta de ingestao e consulta de leituras (a fonte pode ser MQTT, HTTP ou dado de demo)."""

    def adicionar(self, leituras: list[Leitura]) -> int:
        """Grava sem duplicar (sensor, equipamento, ts) ja existentes. Devolve novas linhas."""
        ...

    def consumo_horario(self, sensor_id: str, inicio: datetime, fim: datetime) -> list[ConsumoHora]:
        """kWh somado por hora cheia local (so horas com leitura), em ordem."""
        ...

    def ultimo_ts(self, sensor_id: str) -> datetime | None: ...

    def consumo_por_equipamento(
        self, sensor_id: str, inicio: datetime, fim: datetime
    ) -> list[ConsumoEquipamento]: ...

    def potencia_em(self, sensor_id: str, ts: datetime) -> float: ...


@dataclass(frozen=True)
class ConsumoHora:
    hora: datetime
    kwh: float


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
    """Custo, ranking e faixa tarifaria; a implementacao reusa o pacote M1."""

    def faixas(self, instantes: list[datetime], modalidade: str) -> list[str]: ...

    def custo_por_faixa(
        self, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str
    ) -> list[CustoLinha]: ...

    def ranking(
        self, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str, n: int
    ) -> list[RankingLinha]: ...



class ResultadosM3Indisponiveis(RuntimeError):
    """O artefato do M3 que a empresa tem direito de ver esta ausente, ilegivel ou fora do esquema."""


class ResultadosM3Repositorio(Protocol):
    """Resultados offline do M3 (modelos, alertas, antes x depois).

    Devolve `None` quando a empresa nao tem resultados (artefatos do demo pertencem so a empresa
    demo: outra empresa recebe vazio, nunca os dados dela). Levanta `ResultadosM3Indisponiveis`
    quando a empresa teria direito mas o artefato nao pode ser lido.
    """

    def resumo(self, empresa_id: str) -> ResumoM3 | None: ...
    def alertas(self, empresa_id: str) -> AlertasM3 | None: ...
    def economia(self, empresa_id: str) -> EconomiaM3 | None: ...
    def previsao(self, empresa_id: str) -> EstudoPrevisao | None: ...
