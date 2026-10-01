"""Relogio, ids, chaves de dispositivo e atuador simulado."""

from __future__ import annotations

import itertools
import uuid
from datetime import UTC, datetime, timedelta

from mapen_plataforma.domain.comando import ESTADO_INICIAL, Acao, EstadoRele


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


class ChavesEmMemoria:
    """Chave HMAC por dispositivo. Chaves reais (provisionamento, rotacao) ainda nao existem."""

    def __init__(self, chaves: dict[str, bytes] | None = None) -> None:
        self._chaves: dict[str, bytes] = dict(chaves or {})

    def definir(self, device_id: str, chave: bytes) -> None:
        self._chaves[device_id] = chave

    def chave(self, device_id: str) -> bytes | None:
        return self._chaves.get(device_id)


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
