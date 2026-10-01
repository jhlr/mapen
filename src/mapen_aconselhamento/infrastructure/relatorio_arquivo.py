"""Escritor do relatorio no sistema de arquivos."""

from __future__ import annotations

from pathlib import Path


def escrever_relatorio(texto: str, diretorio: Path, sensor_id: str, mes: str) -> Path:
    """Grava o relatorio em `diretorio/<sensor_id>_<mes>.md`."""
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / f"{sensor_id}_{mes}.md"
    destino.write_text(texto, encoding="utf-8")
    return destino
