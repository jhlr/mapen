"""Relogio, ids, chaves de dispositivo e atuador simulado."""

from __future__ import annotations

import itertools
import uuid
from datetime import UTC, datetime, timedelta

from mapen_plataforma.application.portas import CredenciaisDispositivoRepo, DerivadorChave
from mapen_plataforma.domain.comando import ESTADO_INICIAL, Acao, EstadoRele
from mapen_plataforma.domain.credenciais import derivar_chave_comando


class RelogioSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)


class RelogioFixo:
    """Relogio de teste: so anda quando `avancar` e chamado."""

    def __init__(self, instante: datetime) -> None:
        self._instante = instante

    def agora(self) -> datetime:
        return self._instante

    def avancar(self, segundos: float) -> None:
        self._instante += timedelta(seconds=segundos)


class GeradorUuid:
    def novo(self) -> str:
        return uuid.uuid4().hex


class GeradorSequencial:
    """Ids previsiveis para teste."""

    def __init__(self, prefixo: str = "id") -> None:
        self._contador = itertools.count(1)
        self._prefixo = prefixo

    def novo(self) -> str:
        return f"{self._prefixo}-{next(self._contador)}"


class DerivadorHmac:
    """Chave de comando = HMAC(segredo mestre do servidor, device_id|sal). O segredo nunca vai ao banco."""

    def __init__(self, segredo_mestre: bytes) -> None:
        if len(segredo_mestre) < 32:
            raise ValueError("segredo mestre deve ter ao menos 32 bytes")
        self._segredo = segredo_mestre

    def derivar(self, device_id: str, sal: str) -> bytes:
        return derivar_chave_comando(self._segredo, device_id, sal)


class ChavesDerivadas:
    """Chave de comando do dispositivo: derivada do sal guardado. Rotacionar o sal invalida a anterior."""

    def __init__(self, credenciais: CredenciaisDispositivoRepo, derivador: DerivadorChave) -> None:
        self._credenciais = credenciais
        self._derivador = derivador

    def chave(self, device_id: str) -> bytes | None:
        credencial = self._credenciais.obter(device_id)
        return None if credencial is None else self._derivador.derivar(device_id, credencial.sal)


class AtuadorSimulado:
    """Rele simulado em memoria; apos 'reinicio' (nova instancia) tudo volta energizado."""

    def __init__(self) -> None:
        self._estados: dict[tuple[str, str], EstadoRele] = {}

    def aplicar(self, device_id: str, equipamento_id: str, acao: Acao) -> None:
        self._estados[(device_id, equipamento_id)] = (
            EstadoRele.DESLIGADO if acao is Acao.DESLIGAR else EstadoRele.ENERGIZADO
        )

    def estado(self, device_id: str, equipamento_id: str) -> EstadoRele:
        return self._estados.get((device_id, equipamento_id), ESTADO_INICIAL)
