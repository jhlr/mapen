"""API -> DuckDB -> custo do M1, com dado sintetico exato e com o CU-BEMS de demo."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ambiente import Ambiente, bearer, sem_m3
from mapen_aconselhamento.domain.custo import custo_por_faixa
from mapen_aconselhamento.infrastructure.duckdb_leituras import ler_leituras
from mapen_aconselhamento.infrastructure.tarifa_csv import carregar_tarifas
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.demo import EMPRESA_DEMO, EMPRESA_OUTRA, SENSOR_CU_BEMS, semear_demo
from mapen_plataforma.infrastructure.servicos import AtuadorSimulado, DerivadorHmac, GeradorSequencial, RelogioSistema
from mapen_plataforma.interface.api.app import criar_app
from mapen_plataforma.interface.api.composicao import DB_M1, montar_provisionamento, montar_servicos

PONTA, INTERM = 1.62479, 1.05341
INICIO, FIM = "2026-10-05T00:00:00-03:00", "2026-10-06T00:00:00-03:00"


def test_custo_via_api_bate_com_valor_calculado_a_mao(amb: Ambiente) -> None:
    # sa: AC1 a 2 kW, 17:00-17:59 (intermediario) e 18:00-18:59 (ponta), segunda 2026-10-05.
    resposta = amb.client.get(f"/sensores/sa/custo?inicio={INICIO}&fim={FIM}&modalidade=branca", headers=amb.ha)
    assert resposta.status_code == 200
    por_faixa = {x["faixa"]: x for x in resposta.json()}
    assert por_faixa["intermediario"]["kwh"] == pytest.approx(2.0)
    assert por_faixa["ponta"]["kwh"] == pytest.approx(2.0)
    assert por_faixa["intermediario"]["custo_rs"] == pytest.approx(2.0 * INTERM)
    assert por_faixa["ponta"]["custo_rs"] == pytest.approx(2.0 * PONTA)


def test_api_usa_exatamente_o_calculo_do_m1(amb: Ambiente) -> None:
    leituras = ler_leituras(
        amb.banco.conexao, "sa", pd.Timestamp("2026-10-05T00:00:00"), pd.Timestamp("2026-10-06T00:00:00")
    )
    direto = custo_por_faixa(leituras, carregar_tarifas(), "convencional")
    via_api: list[dict[str, Any]] = amb.client.get(
        f"/sensores/sa/custo?inicio={INICIO}&fim={FIM}&modalidade=convencional", headers=amb.ha
    ).json()
    assert sum(x["custo_rs"] for x in via_api) == pytest.approx(float(direto["custo_rs"].sum()))
    assert via_api[0]["faixa"] == "unico"


def test_ranking_ordena_por_custo(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {
        "leituras": [{"equipamento": "Light", "ts": "2026-10-05T17:00:00-03:00", "potencia_w": 60000.0, "kwh": 1.0}]
    }
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=bearer(amb.tokens["sa"])).json() == {"gravadas": 1}
    ranking = amb.client.get(f"/sensores/sa/ranking?inicio={INICIO}&fim={FIM}&n=5", headers=amb.ha).json()
    assert [r["equipamento"] for r in ranking] == ["AC1", "Light"]
    assert ranking[0]["custo_rs"] == pytest.approx(2.0 * INTERM + 2.0 * PONTA)


def test_reenvio_de_lote_nao_duplica(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-05T17:00:00-03:00", "kwh": 99.0}]}
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=bearer(amb.tokens["sa"])).json() == {"gravadas": 0}
    novo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-06T10:00:00-03:00", "kwh": 1.0}] * 2}
    assert amb.client.post("/sensores/sa/leituras", json=novo, headers=bearer(amb.tokens["sa"])).json() == {"gravadas": 1}
    assert amb.client.post("/sensores/sa/leituras", json=novo, headers=bearer(amb.tokens["sa"])).json() == {"gravadas": 0}


def test_consumo_agora_e_hoje(amb: Ambiente) -> None:
    dados = amb.client.get("/sensores/sa/consumo-agora", headers=amb.ha).json()
    assert dados["ts_referencia"] == "2026-10-05T18:59:00-03:00"
    assert dados["potencia_w"] == pytest.approx(2000.0)
    assert dados["kwh_dia"] == pytest.approx(4.0)
    assert dados["por_equipamento"] == [{"equipamento": "AC1", "kwh": pytest.approx(4.0)}]


def test_periodo_e_modalidade_invalidos(amb: Ambiente) -> None:
    assert amb.client.get(f"/sensores/sa/custo?inicio={FIM}&fim={INICIO}", headers=amb.ha).status_code == 422
    assert amb.client.get(
        f"/sensores/sa/custo?inicio={INICIO}&fim={FIM}&modalidade=xyz", headers=amb.ha
    ).status_code == 422


@pytest.mark.skipif(not DB_M1.exists(), reason="banco do M1 (data/mapen_m1.duckdb) ausente")
def test_demo_cu_bems_ate_o_custo_real_do_m1(tmp_path: Path) -> None:
    copia = tmp_path / "demo.duckdb"
    shutil.copy2(DB_M1, copia)
    banco = BancoDuckDB(copia)
    ids, derivador = GeradorSequencial(), DerivadorHmac(b"m" * 32)
    provisionar, emitir = montar_provisionamento(banco, ids, derivador)
    segredos = {s.empresa_id: s for s in semear_demo(banco, provisionar, emitir)}
    servicos = montar_servicos(
        banco, RelogioSistema(), ids, derivador, AtuadorSimulado(), CalculadoraM1(banco), sem_m3(EMPRESA_DEMO)
    )
    client = TestClient(criar_app(servicos))
    demo, outra = bearer(segredos[EMPRESA_DEMO].chave_api), bearer(segredos[EMPRESA_OUTRA].chave_api)
    assert [s["id"] for s in client.get("/sensores", headers=demo).json()] == [SENSOR_CU_BEMS]
    equipamentos = client.get("/equipamentos", headers=demo).json()
    assert len(equipamentos) == 24
    assert {e["nome"]: e["critico"] for e in equipamentos}["z1_AC1"] is False  # classificado no YAML
    assert client.get(f"/sensores/{SENSOR_CU_BEMS}/consumo-agora", headers=outra).status_code == 404

    periodo = "inicio=2018-08-01T00:00:00-03:00&fim=2018-09-01T00:00:00-03:00"
    custo = client.get(f"/sensores/{SENSOR_CU_BEMS}/custo?{periodo}&modalidade=convencional", headers=demo).json()
    # Valor do relatorio real do M1 (docs/m1_notas.md): R$ 17725.21 convencional.
    assert sum(x["custo_rs"] for x in custo) == pytest.approx(17725.21, abs=0.01)
    ranking = client.get(f"/sensores/{SENSOR_CU_BEMS}/ranking?{periodo}&n=3", headers=demo).json()
    assert len(ranking) == 3 and ranking[0]["custo_rs"] >= ranking[1]["custo_rs"] >= ranking[2]["custo_rs"]


def test_critico_inicial_falha_fechada_para_o_que_o_yaml_nao_classifica() -> None:
    from mapen_aconselhamento.infrastructure.equipamentos_yaml import carregar_config_equipamentos
    from mapen_plataforma.infrastructure.demo import critico_inicial

    config = carregar_config_equipamentos()
    assert critico_inicial(config, "z1_AC1") is False
    assert critico_inicial(config, "z1_Light") is False
    assert critico_inicial(config, "z1_Bomba_UTI") is True  # nao casa com nenhum padrao
    assert config.para("z1_Bomba_UTI").critico is False  # o padrao do M1 seria fail-open
    assert config.encontrar("z1_Bomba_UTI") is None


def test_422_nao_ecoa_o_valor_recebido(amb: Ambiente) -> None:
    comando = amb.comando()
    comando["assinatura"] = "segredo-que-nao-deve-voltar"
    corpo = {"equipamento_id": "eq-ac", "comando": comando}
    resposta = amb.client.post("/desligamentos", json=corpo, headers=amb.ha)
    assert resposta.status_code == 422
    assert "segredo-que-nao-deve-voltar" not in resposta.text
