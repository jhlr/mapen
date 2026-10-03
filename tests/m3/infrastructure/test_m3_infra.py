from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_aconselhamento.infrastructure.duckdb_leituras import conectar, inserir_leituras
from mapen_modelos.domain.features import FEATURES
from mapen_modelos.infrastructure.lightgbm_modelo import TreinadorLightGBM
from mapen_modelos.infrastructure.serie_duckdb import SeriesHorariasDuckDB
from mapen_modelos.infrastructure.shap_explicador import ExplicadorShap

T0 = pd.Timestamp("2026-10-05")


def test_leitor_agrega_minuto_em_hora_e_marca_hora_incompleta_como_nan() -> None:
    idx = pd.date_range(T0, periods=180, freq="1min")  # 3 horas
    largo = pd.DataFrame({"z1_AC1": 6.0, "z1_Light": np.arange(180, dtype=float)}, index=idx)
    largo.iloc[70, 0] = np.nan  # um minuto ausente na hora 1 do AC
    con = conectar()
    inserir_leituras(con, largo, "s", "1min", 1000.0, 0, "erro")
    out = SeriesHorariasDuckDB(con).ler_series_horarias("s", T0, T0 + pd.Timedelta(hours=4))
    assert list(out.index) == list(pd.date_range(T0, periods=4, freq="1h"))
    assert out["z1_AC1"].iloc[0] == pytest.approx(6.0)
    assert pd.isna(out["z1_AC1"].iloc[1])  # hora com minuto ausente: NaN, sem interpolar
    assert out["z1_AC1"].iloc[2] == pytest.approx(6.0)
    assert pd.isna(out["z1_AC1"].iloc[3])  # hora sem nenhuma leitura no banco
    assert out["z1_Light"].iloc[0] == pytest.approx(np.arange(60).mean())


def test_leitor_sem_dados_falha() -> None:
    with pytest.raises(ValueError):
        SeriesHorariasDuckDB(conectar()).ler_series_horarias("nada", T0, T0 + pd.Timedelta(hours=1))


def test_explicador_bate_com_a_previsao_e_exige_modelo_lightgbm() -> None:
    rng = np.random.default_rng(0)
    x = pd.DataFrame(rng.normal(size=(300, len(FEATURES))), columns=list(FEATURES))
    y = pd.Series(2.0 * x["kw_lag1"] + rng.normal(0, 0.1, 300))
    modelo = TreinadorLightGBM(n_arvores=40).treinar(x, y)
    valores = ExplicadorShap().valores(modelo, x)
    assert valores.shape == x.shape
    mean_abs = np.abs(valores).mean(axis=0)
    assert FEATURES[int(np.argmax(mean_abs))] == "kw_lag1"

    class Outro:
        def prever(self, x: pd.DataFrame) -> np.ndarray:
            return np.zeros(len(x))

    with pytest.raises(TypeError):
        ExplicadorShap().valores(Outro(), x)
