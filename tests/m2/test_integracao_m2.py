"""API -> DuckDB -> custo do M1, com dado sintetico exato e com o CU-BEMS de demo."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ambiente import HA, Ambiente
from mapen_aconselhamento.custo import custo_por_faixa
from mapen_aconselhamento.ingest import ler_leituras
from mapen_aconselhamento.tarifa import Tarifas
from mapen_plataforma.domain.comando import ConfiguracaoSeguranca
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.demo import EMPRESA_DEMO, EMPRESA_OUTRA, SENSOR_CU_BEMS, semear_demo
from mapen_plataforma.infrastructure.servicos import (
    AtuadorSimulado,
    ChavesEmMemoria,
    GeradorSequencial,
    RelogioSistema,
)
from mapen_plataforma.interface.api.app import criar_app
from mapen_plataforma.interface.api.composicao import DB_M1, montar_servicos

PONTA, INTERM = 1.62479, 1.05341
INICIO, FIM = "2026-10-05T00:00:00", "2026-10-06T00:00:00"


def test_custo_via_api_bate_com_valor_calculado_a_mao(amb: Ambiente) -> None:
    # sa: AC1 a 2 kW, 17:00-17:59 (intermediario) e 18:00-18:59 (ponta), segunda 2026-10-05.
    resposta = amb.client.get(f"/sensores/sa/custo?inicio={INICIO}&fim={FIM}&modalidade=branca", headers=HA)
    assert resposta.status_code == 200
    por_faixa = {x["faixa"]: x for x in resposta.json()}
    assert por_faixa["intermediario"]["kwh"] == pytest.approx(2.0)
    assert por_faixa["ponta"]["kwh"] == pytest.approx(2.0)
    assert por_faixa["intermediario"]["custo_rs"] == pytest.approx(2.0 * INTERM)
    assert por_faixa["ponta"]["custo_rs"] == pytest.approx(2.0 * PONTA)


def test_api_usa_exatamente_o_calculo_do_m1(amb: Ambiente) -> None:
    leituras = ler_leituras(amb.banco.conexao, "sa", pd.Timestamp(INICIO), pd.Timestamp(FIM))
    direto = custo_por_faixa(leituras, Tarifas.carregar(), "convencional")
    via_api: list[dict[str, Any]] = amb.client.get(
        f"/sensores/sa/custo?inicio={INICIO}&fim={FIM}&modalidade=convencional", headers=HA
    ).json()
    assert sum(x["custo_rs"] for x in via_api) == pytest.approx(float(direto["custo_rs"].sum()))
    assert via_api[0]["faixa"] == "unico"


def test_ranking_ordena_por_custo(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {
        "leituras": [{"equipamento": "Light", "ts": "2026-10-05T17:00:00", "potencia_w": 60000.0, "kwh": 1.0}]
    }
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=HA).json() == {"gravadas": 1}
    ranking = amb.client.get(f"/sensores/sa/ranking?inicio={INICIO}&fim={FIM}&n=5", headers=HA).json()
    assert [r["equipamento"] for r in ranking] == ["AC1", "Light"]
    assert ranking[0]["custo_rs"] == pytest.approx(2.0 * INTERM + 2.0 * PONTA)


def test_reenvio_de_lote_nao_duplica(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-05T17:00:00", "kwh": 99.0}]}
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=HA).json() == {"gravadas": 0}
    novo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-06T10:00:00", "kwh": 1.0}] * 2}
    assert amb.client.post("/sensores/sa/leituras", json=novo, headers=HA).json() == {"gravadas": 1}
    assert amb.client.post("/sensores/sa/leituras", json=novo, headers=HA).json() == {"gravadas": 0}


def test_consumo_agora_e_hoje(amb: Ambiente) -> None:
    dados = amb.client.get("/sensores/sa/consumo-agora", headers=HA).json()
    assert dados["ts_referencia"] == "2026-10-05T18:59:00"
    assert dados["potencia_w"] == pytest.approx(2000.0)
    assert dados["kwh_dia"] == pytest.approx(4.0)
    assert dados["por_equipamento"] == [{"equipamento": "AC1", "kwh": pytest.approx(4.0)}]


def test_periodo_e_modalidade_invalidos(amb: Ambiente) -> None:
    assert amb.client.get(f"/sensores/sa/custo?inicio={FIM}&fim={INICIO}", headers=HA).status_code == 422
    assert amb.client.get(
        f"/sensores/sa/custo?inicio={INICIO}&fim={FIM}&modalidade=xyz", headers=HA
    ).status_code == 422


@pytest.mark.skipif(not DB_M1.exists(), reason="banco do M1 (data/mapen_m1.duckdb) ausente")
def test_demo_cu_bems_ate_o_custo_real_do_m1(tmp_path: Path) -> None:
    copia = tmp_path / "demo.duckdb"
    shutil.copy2(DB_M1, copia)
    banco = BancoDuckDB(copia)
    semear_demo(banco)
    servicos = montar_servicos(
        banco, RelogioSistema(), GeradorSequencial(), ChavesEmMemoria(), AtuadorSimulado(),
        CalculadoraM1(banco), ConfiguracaoSeguranca(),
    )
    client = TestClient(criar_app(servicos))
    demo, outra = {"X-Empresa-Id": EMPRESA_DEMO}, {"X-Empresa-Id": EMPRESA_OUTRA}
    assert [s["id"] for s in client.get("/sensores", headers=demo).json()] == [SENSOR_CU_BEMS]
    assert len(client.get("/equipamentos", headers=demo).json()) == 24
    assert client.get(f"/sensores/{SENSOR_CU_BEMS}/consumo-agora", headers=outra).status_code == 404

    periodo = "inicio=2018-08-01T00:00:00&fim=2018-09-01T00:00:00"
    custo = client.get(f"/sensores/{SENSOR_CU_BEMS}/custo?{periodo}&modalidade=convencional", headers=demo).json()
    # Valor do relatorio real do M1 (docs/m1_notas.md): R$ 17725.21 convencional.
    assert sum(x["custo_rs"] for x in custo) == pytest.approx(17725.21, abs=0.01)
    ranking = client.get(f"/sensores/{SENSOR_CU_BEMS}/ranking?{periodo}&n=3", headers=demo).json()
    assert len(ranking) == 3 and ranking[0]["custo_rs"] >= ranking[1]["custo_rs"] >= ranking[2]["custo_rs"]
