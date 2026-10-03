"""Caminhos padrao do repositorio (dados e configuracao)."""

from __future__ import annotations

from pathlib import Path

RAIZ: Path = Path(__file__).resolve().parents[3]
CSV_TARIFAS_PADRAO: Path = RAIZ / "data" / "tarifas" / "neoenergia_pe.csv"
YAML_EQUIPAMENTOS_PADRAO: Path = RAIZ / "config" / "equipamentos.yaml"
