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


def test_ranking_desempata_por_nome_do_ativo() -> None:
    # Empate exato na soma dos positivos: a ordem não pode depender da versão do pandas.
    # O painel (dashboard/calculo.js) desempata por nome, e a conferência cruzada compara posição a posição.
    # Com 8 ativos e 4 empatados em zero, pandas 3.0.x devolvia z1_Plug antes de z1_Light.
    ativos = ["z1_AC1", "z1_Light", "z1_Plug", "z2_Light", "z2_Plug", "z3_Light", "z4_AC1", "z4_Plug"]
    positivos = {"z1_AC1": 66.2, "z4_AC1": 38.4, "z2_Light": 4.1, "z3_Light": 1.9}
    d = pd.DataFrame({"ativo": ativos, "data": pd.to_datetime(["2018-11-04"] * 8), "kwh": 1.0, "esperado": 1.0,
                      "desvio": [positivos.get(a, 0.0) for a in ativos]})
    rk = av.ranking(d)
    assert list(rk["ativo"]) == ["z1_AC1", "z4_AC1", "z2_Light", "z3_Light", "z1_Light", "z1_Plug", "z2_Plug", "z4_Plug"]


def test_rotulos_traduzem_o_codigo_do_ativo_em_nome_legivel() -> None:
    r = av.rotulos_ativos(["z1_AC1", "z2_Light", "z4_Plug", "z9_AC12", "estranho"], {"z4_Plug": 0.0, "z1_AC1": 59.6})
    assert r["z1_AC1"]["nome"] == "Ar-condicionado 1" and r["z1_AC1"]["zona"] == 1
    assert r["z1_AC1"]["completo"] == "Ar-condicionado 1 · zona 1"
    assert r["z2_Light"]["nome"] == "Iluminação" and r["z2_Light"]["completo"] == "Iluminação · zona 2"
    assert r["z9_AC12"]["nome"] == "Ar-condicionado 12"
    assert "nunca consumiu" in str(r["z4_Plug"]["nota"]).lower() and r["z1_AC1"]["nota"] == ""  # nota só quando o máximo do recorte é 0


def test_rotulo_de_codigo_desconhecido_cai_no_proprio_codigo() -> None:
    r = av.rotulos_ativos(["estranho"], {"estranho": 1.0})
    assert r["estranho"]["nome"] == "estranho" and r["estranho"]["completo"] == "estranho" and r["estranho"]["zona"] is None
