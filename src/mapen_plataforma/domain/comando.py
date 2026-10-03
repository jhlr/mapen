"""Comando de rele assinado por dispositivo (HMAC-SHA256) e a politica de seguranca.

Funcoes puras: relogio, estado de nonce e flag chegam como argumento.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_plataforma.domain.entidades import Equipamento, ErroDominio
from mapen_plataforma.domain.tempo import exigir_fuso

MAX_TTL = timedelta(seconds=60)
"""Vida maxima de um comando: `validade - emitido_em`."""
TOLERANCIA_RELOGIO = timedelta(seconds=5)
"""Desvio de relogio aceito entre quem assina e o servidor."""
PADRAO_ASSINATURA = re.compile(r"^[0-9a-f]{64}$")


class Acao(enum.StrEnum):
    DESLIGAR = "desligar"
    LIGAR = "ligar"


class Motivo(enum.StrEnum):
    COMANDO_MALFORMADO = "comando_malformado"
    EQUIPAMENTO_DESCONHECIDO = "equipamento_desconhecido"
    DISPOSITIVO_DIVERGENTE = "dispositivo_divergente"
    ASSINATURA_INVALIDA = "assinatura_invalida"
    TTL_EXCESSIVO = "ttl_excessivo"
    EMISSAO_FUTURA = "emissao_futura"
    VALIDADE_VENCIDA = "validade_vencida"
    NONCE_REPETIDO = "nonce_repetido"
    REGRA_INVALIDA = "regra_invalida"
    EQUIPAMENTO_CRITICO = "equipamento_critico"
    SEM_AUTORIZACAO = "sem_autorizacao"
    DESLIGAMENTO_REMOTO_DESABILITADO = "desligamento_remoto_desabilitado"
    FALHA_ATUADOR = "falha_atuador"


@dataclass(frozen=True)
class ComandoRele:
    """O que a assinatura autoriza: dispositivo, empresa, equipamento, acao, nonce e janela de tempo."""

    device_id: str
    empresa_id: str
    equipamento_id: str
    acao: Acao
    nonce: str
    emitido_em: datetime
    validade: datetime
    assinatura: str

    def __post_init__(self) -> None:
        exigir_fuso(self.emitido_em, "emitido_em")
        exigir_fuso(self.validade, "validade")

    def mensagem(self) -> bytes:
        return mensagem_assinada(
            self.device_id, self.empresa_id, self.equipamento_id, self.acao, self.nonce,
            self.emitido_em, self.validade,
        )


def mensagem_assinada(
    device_id: str,
    empresa_id: str,
    equipamento_id: str,
    acao: Acao,
    nonce: str,
    emitido_em: datetime,
    validade: datetime,
) -> bytes:
    """JSON canonico (chaves ordenadas, sem espacos); instantes em epoch s inteiro."""
    corpo = {
        "device_id": device_id,
        "empresa_id": empresa_id,
        "equipamento_id": equipamento_id,
        "acao": acao.value,
        "nonce": nonce,
        "emitido_em": int(emitido_em.timestamp()),
        "validade": int(validade.timestamp()),
    }
    return json.dumps(corpo, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def assinar(
    chave: bytes,
    device_id: str,
    empresa_id: str,
    equipamento_id: str,
    acao: Acao,
    nonce: str,
    emitido_em: datetime,
    validade: datetime,
) -> str:
    mensagem = mensagem_assinada(device_id, empresa_id, equipamento_id, acao, nonce, emitido_em, validade)
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def assinatura_valida(comando: ComandoRele, chave: bytes) -> bool:
    """Compara bytes: texto nao ASCII nunca derruba a comparacao."""
    esperada = hmac.new(chave, comando.mensagem(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada.encode(), comando.assinatura.encode())


@dataclass(frozen=True)
class ConfiguracaoSeguranca:
    """`desligamento_remoto_habilitado` comeca falso: o primeiro uso real e so recomendacao."""

    desligamento_remoto_habilitado: bool = False


@dataclass(frozen=True)
class Decisao:
    aceito: bool
    motivo: Motivo | None = None


def _rejeitar(motivo: Motivo) -> Decisao:
    return Decisao(False, motivo)


def avaliar_comando(
    comando: ComandoRele,
    chave: bytes | None,
    agora: datetime,
    consumir_nonce: Callable[[], bool],
    equipamento: Equipamento,
    regra_valida: bool,
    autorizado_por: str | None,
    config: ConfiguracaoSeguranca,
) -> Decisao:
    """Dono da ordem das checagens; a primeira violada rejeita.

    Autenticidade (dispositivo, assinatura, janela de tempo) vem antes do nonce, para que um
    comando que falha nisso nao gaste o nonce. `consumir_nonce` (efeito colateral, atomico,
    devolve False se repetido) so e chamado depois, e antes das regras de negocio.
    """
    if comando.device_id != equipamento.sensor_id:
        return _rejeitar(Motivo.DISPOSITIVO_DIVERGENTE)
    if chave is None or not assinatura_valida(comando, chave):
        return _rejeitar(Motivo.ASSINATURA_INVALIDA)
    if comando.validade - comando.emitido_em > MAX_TTL or comando.validade < comando.emitido_em:
        return _rejeitar(Motivo.TTL_EXCESSIVO)
    if comando.emitido_em > agora + TOLERANCIA_RELOGIO:
        return _rejeitar(Motivo.EMISSAO_FUTURA)
    if comando.validade + TOLERANCIA_RELOGIO < agora:
        return _rejeitar(Motivo.VALIDADE_VENCIDA)
    if not consumir_nonce():
        return _rejeitar(Motivo.NONCE_REPETIDO)
    if not regra_valida:
        return _rejeitar(Motivo.REGRA_INVALIDA)
    if equipamento.critico:
        return _rejeitar(Motivo.EQUIPAMENTO_CRITICO)
    if not autorizado_por or not autorizado_por.strip():
        return _rejeitar(Motivo.SEM_AUTORIZACAO)
    if comando.acao is Acao.DESLIGAR and not config.desligamento_remoto_habilitado:
        return _rejeitar(Motivo.DESLIGAMENTO_REMOTO_DESABILITADO)
    return Decisao(True)


def expira_o_nonce_em(comando: ComandoRele) -> datetime:
    """Depois deste instante o comando nao passa mais pela janela, entao o nonce pode ser podado."""
    return comando.validade + TOLERANCIA_RELOGIO


class EstadoRele(enum.StrEnum):
    ENERGIZADO = "energizado"
    DESLIGADO = "desligado"


ESTADO_INICIAL: EstadoRele = EstadoRele.ENERGIZADO
"""Apos reinicio o rele volta energizado, salvo regra explicita (nao implementada)."""
