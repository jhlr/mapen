from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from mapen_etl.interface.cli import main


def test_cli_recarga_e_idempotente_por_padrao_e_fail_protege(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dados = tmp_path / "dados"
    dados.mkdir()
    (dados / "base_diaria.csv").write_text("data,ativo,kwh\n2025-01-01,z1_AC1,10\n", encoding="utf-8")
    (dados / "base_horaria.csv").write_text("inicio_hora,ativo,kw\n2025-01-01 00:00:00,z1_AC1,1\n", encoding="utf-8")
    banco = tmp_path / "etl.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{banco}")

    assert main(["--data-dir", str(dados)]) == 0
    assert "base_diaria: 1 linhas gravadas." in capsys.readouterr().out
    assert main(["--data-dir", str(dados)]) == 0  # replace: reexecutar nao duplica
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("SELECT count(*) FROM base_horaria").fetchone() == (1,)

    with pytest.raises(ValueError, match="already exists"):
        main(["--data-dir", str(dados), "--if-exists", "fail"])
