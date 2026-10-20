from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mapen_etl.domain.bases import BaseAv1
from mapen_etl.infrastructure.leitor_csv import LeitorCsv

BASE = BaseAv1("b.csv", "b", ("data",))


def test_le_tipado_e_registra_procedencia(tmp_path: Path) -> None:
    arq = tmp_path / "b.csv"
    arq.write_text("data,ativo,valido\n2025-01-01,z1_AC1,True\n2025-01-02,z1_AC1,False\n", encoding="utf-8")

    df = LeitorCsv().ler(BASE, arq)

    assert list(df.columns) == ["source_file", "source_row", "data", "ativo", "valido"]
    assert df["source_file"].tolist() == ["b.csv", "b.csv"]
    assert df["source_row"].tolist() == [1, 2]
    assert pd.api.types.is_datetime64_any_dtype(df["data"])
    assert df["valido"].tolist() == [True, False]


def test_recusa_arquivo_sem_linhas(tmp_path: Path) -> None:
    arq = tmp_path / "b.csv"
    arq.write_text("data,ativo\n", encoding="utf-8")
    with pytest.raises(ValueError, match="nao contem linhas"):
        LeitorCsv().ler(BASE, arq)


def test_recusa_coluna_reservada(tmp_path: Path) -> None:
    arq = tmp_path / "b.csv"
    arq.write_text("data,source_row\n2025-01-01,7\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source_row"):
        LeitorCsv().ler(BASE, arq)
