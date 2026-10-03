"""Gravacao de artefatos (relatorio markdown e JSON) em disco."""

from __future__ import annotations

from pathlib import Path


def escrever_texto(destino: Path, texto: str) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    return destino
