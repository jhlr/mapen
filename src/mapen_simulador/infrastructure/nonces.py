"""Gerador de nonce aleatorio."""

from __future__ import annotations

import uuid


class NonceUuid:
    def novo(self) -> str:
        return uuid.uuid4().hex
