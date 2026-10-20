from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import pytest

from mapen_etl.infrastructure.neon import GravadorNeon


def _linhas(banco: Path) -> list[tuple[str, float]]:
    with closing(sqlite3.connect(banco)) as con:
        return con.execute("SELECT uf, mwh FROM t").fetchall()


def test_modos_fail_append_replace(tmp_path: Path) -> None:
    banco = tmp_path / "etl.sqlite"
    g = GravadorNeon(f"sqlite:///{banco}")
    df = pd.DataFrame({"uf": ["PE", "BA"], "mwh": [10.0, 20.0]})

    assert g.gravar(df, "t", "fail") == 2
    with pytest.raises(ValueError, match="already exists"):
        g.gravar(df, "t", "fail")
    assert g.gravar(df.iloc[:1], "t", "append") == 1
    assert _linhas(banco) == [("PE", 10.0), ("BA", 20.0), ("PE", 10.0)]
    assert g.gravar(df.iloc[:1], "t", "replace") == 1
    assert _linhas(banco) == [("PE", 10.0)]


def test_recusa_nome_de_tabela_invalido() -> None:
    with pytest.raises(ValueError, match="nome da tabela"):
        GravadorNeon("sqlite:///:memory:").gravar(pd.DataFrame({"uf": ["PE"]}), "t; DROP TABLE x", "fail")


def test_recusa_dataframe_vazio() -> None:
    with pytest.raises(ValueError, match="Nao ha dados"):
        GravadorNeon("sqlite:///:memory:").gravar(pd.DataFrame({"uf": []}), "t", "fail")


def test_sem_database_url_falha(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)  # sem .env por perto
    with pytest.raises(ValueError, match="DATABASE_URL"):
        GravadorNeon()


def test_url_neon_ganha_driver_psycopg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert GravadorNeon("postgres://u:p@h/db")._url == "postgresql+psycopg://u:p@h/db"
    assert GravadorNeon("postgresql://u:p@h/db")._url == "postgresql+psycopg://u:p@h/db"
