"""Testes do cálculo (rodar da pasta av1-grupo-3-mapen: python -m pytest codigo -q)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import av1_desvio as av  # noqa: E402


def _diaria(valores: dict[str, float], ativo: str = "X") -> pd.DataFrame:
    datas = pd.to_datetime(list(valores))
    return pd.DataFrame(
        {"data": datas, "ativo": ativo, "kwh": list(valores.values()), "minutos_validos": 1440,
         "valido": True, "tipo_dia": "dia_util", "feriado": False}
    )


def test_desvio_relativo_so_com_esperado_positivo() -> None:
    # 5 segundas na janela de referência (esperado 0) e uma segunda avaliada com 4 kWh
    ref = {f"2018-09-{d:02d}": 0.0 for d in (10, 17, 24)} | {f"2018-10-{d:02d}": 0.0 for d in (1, 8)}
    d = _diaria(ref | {"2018-11-05": 4.0})
    r = av.esperado_diario(d, av.REFERENCIAS[0])
    linha = r[r["data"] == "2018-11-05"].iloc[0]
    assert linha["esperado"] == 0 and linha["desvio"] == 4.0 and np.isnan(linha["desvio_rel_pct"])


def test_esperado_e_mediana_do_mesmo_dia_da_semana_e_exclui_o_periodo_avaliado() -> None:
    ref = {"2018-09-10": 10.0, "2018-09-17": 20.0, "2018-09-24": 30.0, "2018-10-01": 1000.0}
    d = _diaria(ref | {"2018-11-05": 25.0})  # 05/11 é segunda; o próprio 25.0 não entra no esperado
    r = av.esperado_diario(d, av.REFERENCIAS[0])
    linha = r[r["data"] == "2018-11-05"].iloc[0]
    assert linha["esperado"] == 25.0  # mediana de 10, 20, 30, 1000
    assert linha["desvio"] == 0.0


def test_dia_sem_cobertura_vira_ausencia_nao_zero() -> None:
    idx = pd.date_range("2018-11-04", periods=1440, freq="min")
    minuto = pd.DataFrame({a: 1.0 for a in av.ATIVOS}, index=idx)
    minuto.iloc[:200, 0] = np.nan  # 86% presente no primeiro ativo
    diaria = av.base_diaria(minuto)
    p = diaria[(diaria["ativo"] == av.ATIVOS[0])].iloc[0]
    assert not p["valido"] and np.isnan(p["kwh"])
    assert diaria[(diaria["ativo"] == av.ATIVOS[1])].iloc[0]["kwh"] == 24.0  # 1 kW x 24 h


def test_ranking_ordena_por_soma_dos_positivos_nao_pelo_saldo() -> None:
    d = pd.DataFrame({"ativo": ["A", "A", "B"], "data": pd.to_datetime(["2018-11-04"] * 3),
                      "kwh": [10.0, 0.0, 3.0], "esperado": [0.0, 20.0, 1.0], "desvio": [10.0, -20.0, 2.0]})
    rk = av.ranking(d)
    assert list(rk["ativo"]) == ["A", "B"] and rk.iloc[0]["saldo"] == -10.0 and rk.iloc[0]["soma_positivos"] == 10.0
