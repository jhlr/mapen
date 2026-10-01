from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mapen_aconselhamento.ingest import (
    DUPLICADOS_PRIMEIRO,
    TimestampsDuplicadosError,
    carregar_cu_bems,
    conectar,
    ler_duplicados,
    reindexar,
    tratar_duplicados,
)

FREQ = "1h"
T0 = pd.Timestamp("2026-10-05 00:00")


def _frame_com_lacuna() -> pd.DataFrame:
    """Pontos em t0,t1,t4,t5; t2 e t3 (2 consecutivos) faltam."""
    idx = pd.DatetimeIndex([T0 + pd.Timedelta(hours=h) for h in (0, 1, 4, 5)])
    return pd.DataFrame({"p": [1.0, 2.0, 5.0, 6.0]}, index=idx)


def _frame_com_duplicado() -> pd.DataFrame:
    idx = pd.DatetimeIndex([T0, T0 + pd.Timedelta(hours=1), T0 + pd.Timedelta(hours=1)])
    return pd.DataFrame({"p": [1.0, 2.0, 99.0]}, index=idx)


def test_reindexar_marca_lacuna_sem_interpolar() -> None:
    completo = reindexar(_frame_com_lacuna(), FREQ)
    assert len(completo) == 6
    assert list(completo["p"].isna()) == [False, False, True, True, False, False]
    assert completo["p"].notna().sum() == 4  # nenhum valor inventado


def test_duplicados_levantam_erro_com_contagem() -> None:
    with pytest.raises(TimestampsDuplicadosError, match="1 timestamps duplicados"):
        reindexar(_frame_com_duplicado(), FREQ)


def test_tratar_duplicados_primeiro_mantem_a_primeira_e_conta() -> None:
    unico, quantidade = tratar_duplicados(_frame_com_duplicado(), DUPLICADOS_PRIMEIRO)
    assert quantidade == 1
    assert list(unico["p"]) == [1.0, 2.0]


def test_politica_desconhecida_e_rejeitada() -> None:
    with pytest.raises(ValueError, match="politica"):
        tratar_duplicados(_frame_com_duplicado(), "descartar")


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
