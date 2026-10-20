from __future__ import annotations

from pathlib import Path

import pytest

from mapen_etl.application.carregar_bases import carregar_bases
from mapen_etl.domain.bases import BaseAv1, ModoCarga


class LeitorFalso:
    def ler(self, base: BaseAv1, caminho: Path) -> str:
        return f"conteudo:{caminho.name}"


class GravadorFalso:
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, str, ModoCarga]] = []

    def gravar(self, conteudo: str, tabela: str, modo: ModoCarga) -> int:
        self.chamadas.append((tabela, conteudo, modo))
        return 1


def test_grava_so_as_duas_bases_na_ordem(tmp_path: Path) -> None:
    for nome in ("base_diaria.csv", "base_horaria.csv", "neoenergia_pe.csv"):
        (tmp_path / nome).write_text("x\n1\n", encoding="utf-8")
    g = GravadorFalso()

    resultado = carregar_bases(LeitorFalso(), g, tmp_path, "fail")

    assert resultado == {"base_diaria": 1, "base_horaria": 1}
    assert g.chamadas == [
        ("base_diaria", "conteudo:base_diaria.csv", "fail"),
        ("base_horaria", "conteudo:base_horaria.csv", "fail"),
    ]


def test_arquivo_ausente_aborta_antes_de_gravar(tmp_path: Path) -> None:
    (tmp_path / "base_diaria.csv").write_text("x\n1\n", encoding="utf-8")
    g = GravadorFalso()

    with pytest.raises(FileNotFoundError, match="base_horaria.csv"):
        carregar_bases(LeitorFalso(), g, tmp_path, "fail")

    assert g.chamadas == []
