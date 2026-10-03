"""Credenciais: chaves de API e tokens de dispositivo. So o hash SHA-256 e guardado.

A chave de assinatura de comandos nao e guardada: deriva-se de um segredo mestre do servidor
(fora do banco) e de um sal por dispositivo, que muda a cada rotacao.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """Quem fez a chamada autenticada: a empresa e o nome do titular da chave."""

    empresa_id: str
    nome: str


@dataclass(frozen=True)
class CredenciaisNovas:
    """Segredos em texto puro, devolvidos uma unica vez no provisionamento."""

    token: str
    chave_comando: str


def gerar_segredo() -> str:
    return secrets.token_urlsafe(32)


def hash_segredo(segredo: str) -> str:
    return hashlib.sha256(segredo.encode()).hexdigest()


def segredo_confere(segredo: str, hash_guardado: str) -> bool:
    return hmac.compare_digest(hash_segredo(segredo).encode(), hash_guardado.encode())


def derivar_chave_comando(segredo_mestre: bytes, device_id: str, sal: str) -> bytes:
    return hmac.new(segredo_mestre, f"{device_id}|{sal}".encode(), hashlib.sha256).digest()
