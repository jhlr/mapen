from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mapen_aconselhamento.domain.calendario import DUPLICADOS_PRIMEIRO, TimestampsDuplicadosError
from mapen_aconselhamento.infrastructure.cu_bems import carregar_cu_bems
from mapen_aconselhamento.infrastructure.duckdb_leituras import conectar, ler_duplicados


def _csv_cu_bems(caminho: Path, repetir_ultima: bool) -> Path:
    ts = pd.date_range("2026-10-05 00:00", periods=3, freq="1min")
    quadro = pd.DataFrame({"Date": ts, "z1_AC1(kW)": [1.0, 2.0, 3.0], "Temp": [20.0] * 3})
    if repetir_ultima:
        quadro = pd.concat([quadro, quadro.iloc[[2]]], ignore_index=True)
    quadro.to_csv(caminho, index=False)
    return caminho


def test_carga_com_duplicado_falha_por_padrao_e_registra_com_politica(tmp_path: Path) -> None:
    csv = _csv_cu_bems(tmp_path / "f.csv", repetir_ultima=True)
    inicio, fim = pd.Timestamp("2026-10-05 00:00"), pd.Timestamp("2026-10-05 00:03")
    con = conectar()
    with pytest.raises(TimestampsDuplicadosError):
        carregar_cu_bems(con, csv, "pred", inicio, fim)
    assert carregar_cu_bems(con, csv, "pred", inicio, fim, duplicados=DUPLICADOS_PRIMEIRO) == 3
    assert ler_duplicados(con, "pred") == (1, DUPLICADOS_PRIMEIRO)
