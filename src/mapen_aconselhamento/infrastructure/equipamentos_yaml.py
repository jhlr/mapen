"""Leitor do YAML de equipamentos: so I/O; a validacao das regras vive no dominio."""

from __future__ import annotations

from pathlib import Path

import yaml

from mapen_aconselhamento.domain.equipamentos import ConfigEquipamentos
from mapen_aconselhamento.infrastructure.caminhos import YAML_EQUIPAMENTOS_PADRAO


def carregar_config_equipamentos(caminho: Path = YAML_EQUIPAMENTOS_PADRAO) -> ConfigEquipamentos:
    bruto: object = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return ConfigEquipamentos.de_dict(bruto)
