"""Contrato de camadas (import-linter): roda o contrato real e prova que ele morde."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from importlinter.cli import lint_imports

RAIZ = Path(__file__).resolve().parents[2]


def test_contratos_do_projeto_passam() -> None:
    assert lint_imports(config_filename=str(RAIZ / "pyproject.toml")) == 0


def _lint(raiz: Path) -> subprocess.CompletedProcess[str]:
    codigo = "import sys; from importlinter.cli import lint_imports; sys.exit(lint_imports(config_filename='cfg.ini'))"
    return subprocess.run(
        [sys.executable, "-c", codigo], cwd=raiz, env={"PYTHONPATH": str(raiz)},
        capture_output=True, text=True, check=False,
    )


def _pacote_minimo(raiz: Path, violacao: str) -> None:
    for nome in ("", "domain", "application", "infrastructure", "interface"):
        pasta = raiz / "miniplat" / nome
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "__init__.py").write_text("")
    if violacao:
        (raiz / "miniplat" / "domain" / "ruim.py").write_text(violacao)
    (raiz / "cfg.ini").write_text(textwrap.dedent("""\
        [importlinter]
        root_package = miniplat
        include_external_packages = True

        [importlinter:contract:camadas]
        name = camadas
        type = layers
        layers =
            miniplat.interface
            miniplat.infrastructure
            miniplat.application
            miniplat.domain

        [importlinter:contract:io]
        name = sem io
        type = forbidden
        source_modules = miniplat.domain
        forbidden_modules = duckdb
    """))


def test_contrato_fica_verde_sem_violacao(tmp_path: Path) -> None:
    _pacote_minimo(tmp_path, "")
    resultado = _lint(tmp_path)
    assert resultado.returncode == 0, resultado.stdout


def test_contrato_fica_vermelho_com_dominio_importando_infraestrutura(tmp_path: Path) -> None:
    _pacote_minimo(tmp_path, "import miniplat.infrastructure\n")
    resultado = _lint(tmp_path)
    assert resultado.returncode != 0
    assert "BROKEN" in resultado.stdout


def test_contrato_fica_vermelho_com_dominio_importando_duckdb(tmp_path: Path) -> None:
    _pacote_minimo(tmp_path, "import duckdb\n")
    resultado = _lint(tmp_path)
    assert resultado.returncode != 0
    assert "BROKEN" in resultado.stdout
