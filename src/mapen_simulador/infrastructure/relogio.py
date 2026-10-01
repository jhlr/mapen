"""Adaptadores de relogio."""

from __future__ import annotations

from datetime import UTC, datetime


class RelogioSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)
