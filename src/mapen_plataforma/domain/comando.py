"""Comando de rele assinado por dispositivo (HMAC-SHA256) e as regras de seguranca.

Funcoes puras: relogio, estado de nonce e flag chegam como argumento.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime

from mapen_plataforma.domain.entidades import Equipamento, ErroDominio


class Acao(enum.StrEnum):
    DESLIGAR = "desligar"
    LIGAR = "ligar"


class Motivo(enum.StrEnum):
    ASSINATURA_INVALIDA = "assinatura_invalida"
    VALIDADE_VENCIDA = "validade_vencida"
    NONCE_REPETIDO = "nonce_repetido"
    DESLIGAMENTO_REMOTO_DESABILITADO = "desligamento_remoto_desabilitado"
    EQUIPAMENTO_CRITICO = "equipamento_critico"
    SEM_AUTORIZACAO = "sem_autorizacao"
    DISPOSITIVO_DIVERGENTE = "dispositivo_divergente"


@dataclass(frozen=True)
class ComandoRele:
    device_id: str
    acao: Acao
    nonce: str
    validade: datetime
    assinatura: str

    def __post_init__(self) -> None:
        if self.validade.tzinfo is None:
            raise ErroDominio("validade deve ter fuso (UTC)")

    def mensagem(self) -> bytes:
        return mensagem_assinada(self.device_id, self.acao, self.nonce, self.validade)


def mensagem_assinada(device_id: str, acao: Acao, nonce: str, validade: datetime) -> bytes:
    """Bytes canonicos assinados: (device_id, acao, nonce, validade em epoch s), separados por '|'."""
    return "|".join([device_id, acao.value, nonce, str(int(validade.timestamp()))]).encode()


def assinar(chave: bytes, device_id: str, acao: Acao, nonce: str, validade: datetime) -> str:
    return hmac.new(chave, mensagem_assinada(device_id, acao, nonce, validade), hashlib.sha256).hexdigest()


def assinatura_valida(comando: ComandoRele, chave: bytes) -> bool:
    esperada = hmac.new(chave, comando.mensagem(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, comando.assinatura)


def autentico(comando: ComandoRele, chave: bytes | None, agora: datetime) -> bool:
    """Assinatura valida e dentro da validade: so entao o nonce pode ser consumido."""
    return chave is not None and assinatura_valida(comando, chave) and comando.validade >= agora


@dataclass(frozen=True)
class ConfiguracaoSeguranca:
    """`desligamento_remoto_habilitado` comeca falso: o primeiro uso real e so recomendacao."""

    desligamento_remoto_habilitado: bool = False


@dataclass(frozen=True)
class Decisao:
    aceito: bool
    motivo: Motivo | None = None


def avaliar_comando(
    comando: ComandoRele,
    chave: bytes | None,
    agora: datetime,
    nonce_repetido: bool,
    equipamento: Equipamento,
    autorizado_por: str | None,
    config: ConfiguracaoSeguranca,
) -> Decisao:
    """Primeira regra violada rejeita; ordem: autenticidade, validade, nonce, depois negocio."""
    if comando.device_id != equipamento.sensor_id:
        return Decisao(False, Motivo.DISPOSITIVO_DIVERGENTE)
    if chave is None or not assinatura_valida(comando, chave):
        return Decisao(False, Motivo.ASSINATURA_INVALIDA)
    if comando.validade < agora:
        return Decisao(False, Motivo.VALIDADE_VENCIDA)
    if nonce_repetido:
        return Decisao(False, Motivo.NONCE_REPETIDO)
    if equipamento.critico:
        return Decisao(False, Motivo.EQUIPAMENTO_CRITICO)
    if not autorizado_por or not autorizado_por.strip():
        return Decisao(False, Motivo.SEM_AUTORIZACAO)
    if comando.acao is Acao.DESLIGAR and not config.desligamento_remoto_habilitado:
        return Decisao(False, Motivo.DESLIGAMENTO_REMOTO_DESABILITADO)
    return Decisao(True)


class EstadoRele(enum.StrEnum):
    ENERGIZADO = "energizado"
    DESLIGADO = "desligado"


ESTADO_INICIAL: EstadoRele = EstadoRele.ENERGIZADO
"""Apos reinicio o rele volta energizado, salvo regra explicita (nao implementada)."""
