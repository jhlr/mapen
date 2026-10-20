import sqlite3
from contextlib import closing

import pandas as pd
import pytest

import main as etl_main
from src.extract import Extract
from src.load import Load
from src.transform import Transform


def test_extracts_csv_and_keeps_source_metadata(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("UF,consumo\nPE,10\n", encoding="utf-8")
    second.write_text("UF,consumo\nBA,20\n", encoding="utf-8")

    result = Extract().extract_from_directory(tmp_path)

    assert result[["UF", "consumo"]].to_dict("records") == [
        {"UF": "PE", "consumo": 10},
        {"UF": "BA", "consumo": 20},
    ]
    assert result["source_file"].tolist() == ["first.csv", "second.csv"]
    assert result["source_row"].tolist() == [1, 1]


def test_extracts_parquet_and_excel_files(tmp_path):
    original = pd.DataFrame({"UF": ["PE"], "Consumo (MWh)": [12.5]})
    parquet = tmp_path / "consumo.parquet"
    excel = tmp_path / "consumo.xlsx"
    original.to_parquet(parquet)
    original.to_excel(excel, index=False)

    parquet_result = Extract().extract_from_directory(parquet)
    excel_result = Extract().extract_from_directory(excel)

    assert parquet_result.loc[0, "Consumo (MWh)"] == 12.5
    assert excel_result.loc[0, "UF"] == "PE"


def test_transform_passes_preprocessed_data_through_unchanged():
    original = pd.DataFrame({"Consumo (MWh)": [12.5], "UF": ["PE"]})

    result = Transform().transform_data(original)

    assert result is original
    assert list(result.columns) == ["Consumo (MWh)", "UF"]
    assert result.iloc[0].to_dict() == {"Consumo (MWh)": 12.5, "UF": "PE"}


def test_transform_passes_empty_preprocessed_data_through():
    original = pd.DataFrame(columns=["Data validada", "Valor (MWh)"])

    assert Transform().transform_data(original) is original


def test_load_writes_to_postgresql_compatible_database(tmp_path):
    database = tmp_path / "etl.sqlite"
    loader = Load(f"sqlite:///{database}")
    df = pd.DataFrame({"uf": ["PE", "BA"], "consumo_mwh": [10.0, 20.0]})

    assert loader.load_neon(df, "consumo") == 2
    assert loader.load_neon(df.iloc[:1], "consumo", if_exists="append") == 1

    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute("SELECT uf, consumo_mwh FROM consumo").fetchall()

    assert rows == [("PE", 10.0), ("BA", 20.0), ("PE", 10.0)]


def test_load_rejects_invalid_table_names():
    loader = Load("sqlite:///:memory:")

    with pytest.raises(ValueError, match="nome da tabela"):
        loader.load_neon(pd.DataFrame({"uf": ["PE"]}), "consumo; DROP TABLE users")


def test_pipeline_loads_only_daily_and_hourly_base_files(tmp_path, monkeypatch):
    (tmp_path / "base_diaria.csv").write_text(
        "data,ativo,kwh\n2025-01-01,z1_AC1,10\n", encoding="utf-8"
    )
    (tmp_path / "base_horaria.csv").write_text(
        "inicio_hora,ativo,kw\n2025-01-01 00:00:00,z1_AC1,1\n",
        encoding="utf-8",
    )
    (tmp_path / "neoenergia_pe.csv").write_text(
        "tarifa\n999\n", encoding="utf-8"
    )
    loaded = []

    class FakeLoad:
        def load_neon(self, df, table, if_exists):
            loaded.append((table, df, if_exists))
            return len(df)

    monkeypatch.setattr(etl_main, "Load", FakeLoad)

    result = etl_main.run_etl(data_dir=tmp_path)

    assert result == {"base_diaria": 1, "base_horaria": 1}
    assert [table for table, _, _ in loaded] == ["base_diaria", "base_horaria"]
    assert all(mode == "replace" for _, _, mode in loaded)
    assert "neoenergia_pe" not in result


def test_pipeline_fails_if_either_base_file_is_missing(tmp_path, monkeypatch):
    (tmp_path / "base_diaria.csv").write_text(
        "data,ativo,kwh\n2025-01-01,z1_AC1,10\n", encoding="utf-8"
    )

    class UnexpectedLoad:
        def __init__(self):
            pytest.fail("Load não deve ser inicializado se faltar um arquivo base")

    monkeypatch.setattr(etl_main, "Load", UnexpectedLoad)

    with pytest.raises(FileNotFoundError, match="base_horaria.csv"):
        etl_main.run_etl(data_dir=tmp_path)
