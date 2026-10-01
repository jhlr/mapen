"""API de resultados do M3: autenticacao, tenant, esquema do artefato, filtros e veredito derivado."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

from ambiente import Ambiente, bearer, montar
from mapen_plataforma.application.portas import ResultadosM3Indisponiveis
from mapen_plataforma.infrastructure.resultados_m3_json import (
    ARQUIVO_ALERTAS,
    ARQUIVO_ECONOMIA,
    ARQUIVO_RESUMO,
    ResultadosM3Json,
)

DIR_REAL = Path(__file__).resolve().parents[2] / "data" / "m3"
JANELA = {"inicio": "2018-07-01T00:00:00", "fim": "2018-11-04T00:00:00"}


def _alerta(eq: str, ts: str, tipo: str, z: float = 5.0, fraca: bool = False) -> dict[str, Any]:
    shap = None if tipo == "zscore" else [
        {"feature": "kw_lag1", "shap": 1.5}, {"feature": "hora", "shap": -0.5}, {"feature": "kw_lag168", "shap": 0.1},
    ]
    return {
        "equipamento": eq, "timestamp": ts, "tipo": tipo, "esperado_kw": 2.0, "observado_kw": 0.5, "z": z,
        "janela_baseline": JANELA, "top_shap": shap, "baseline_fraca": fraca,
        "status": "candidato_nao_corroborado",
    }


def alertas_json() -> dict[str, Any]:
    return {
        "versao_esquema": 1, "sensor_id": "s", "periodo": {"inicio": "2018-11-04T00:00:00", "fim": "2018-12-02T00:00:00"},
        "limiar_z": 4.0, "aviso": "Candidatos nao corroborados.",
        "alertas": [
            _alerta("a", "2018-11-05T09:00:00", "zscore", -6.0),
            _alerta("a", "2018-11-05T10:00:00", "lightgbm", 5.0),
            _alerta("b", "2018-11-06T09:00:00", "zscore", 4.5, fraca=True),
            _alerta("b", "2018-11-07T09:00:00", "lightgbm", 7.0),
            _alerta("a", "2018-11-08T09:00:00", "zscore", -8.0),
        ],
    }


def _eq(nome: str, recuperado: float | None, fraca: bool = False) -> dict[str, Any]:
    return {
        "equipamento": nome, "kwh_antes": 100.0, "kwh_depois": 90.0, "kwh_contrafactual": 105.0, "economia_kwh": 15.0,
        "economia_pct": 14.0, "economia_pct_sem_reducao": 5.0, "recuperado_pct_com_reducao_sintetica": recuperado,
        "reducao_sintetica_aplicada": nome == "a", "baseline_fraca": fraca,
    }


def economia_json(recuperados: dict[str, float | None] | None = None, alvo_dentro: bool = False) -> dict[str, Any]:
    rec = recuperados if recuperados is not None else {"a": 27.0, "b": 15.5, "c": 14.0, "d": None}
    return {
        "versao_esquema": 1, "sensor_id": "s", "natureza": "validacao_de_metodo_sintetica", "aviso": "metodo",
        "periodo_antes": {"inicio": "2018-11-04T00:00:00", "fim": "2018-11-18T00:00:00"},
        "periodo_depois": {"inicio": "2018-11-18T00:00:00", "fim": "2018-12-02T00:00:00"},
        "reducao_sintetica": {"equipamento": "a", "fracao_pct": 15.0, "a_partir_de": "2018-11-18T00:00:00"},
        "recuperado_pct": rec["a"], "tolerancia_pp": 3.0, "dentro_da_tolerancia": alvo_dentro,
        "equipamentos": [_eq(n, v, fraca=(n == "c")) for n, v in rec.items()],
    }


def resumo_json() -> dict[str, Any]:
    por_tipo = [{"tipo": "pico", "detectados": 4, "eventos": 4}, {"tipo": "ligado_continuo", "detectados": 1, "eventos": 2}]
    return {
        "versao_esquema": 1, "sensor_id": "s",
        "dados": {
            "fonte": "CU-BEMS", "periodo": JANELA, "treino": JANELA, "reservado": JANELA,
            "equipamentos_no_andar": 3, "equipamentos_modelados": 2, "equipamentos_sem_carga": ["x"], "linhas_minuto": 100,
        },
        "mae": {
            "unidade": "kW", "horas_teste": 10, "baseline_sazonal": 0.6, "lightgbm": 0.2, "melhora_mediana_pct": 60.0,
            "ressalva_nowcast": "usa lag1",
            "por_equipamento": [
                {"equipamento": "a", "horas_teste": 5, "mae_baseline_kw": 1.0, "mae_lightgbm_kw": 0.5, "melhora_pct": 50.0},
                {"equipamento": "b", "horas_teste": 5, "mae_baseline_kw": 1.0, "mae_lightgbm_kw": 1.2, "melhora_pct": -20.0},
            ],
        },
        "shap": {
            "horas_equipamento": 10, "calendario_pct": 40.0, "historico_pct": 60.0, "limiar_feature_dominante_pct": 50.0,
            "por_feature": [{"feature": "hora", "pct": 40.0}, {"feature": "kw_lag1", "pct": 60.0}],
            "por_equipamento": [
                {"equipamento": "a", "calendario_pct": 30.0, "historico_pct": 70.0, "feature_dominante": "kw_lag1"},
                {"equipamento": "b", "calendario_pct": 60.0, "historico_pct": 40.0, "feature_dominante": None},
            ],
        },
        "benchmark_sintetico": {
            "semente": 1, "eventos_por_tipo_por_equipamento": 2, "limiar_z": 4.0,
            "detectores": [
                {"detector": d, "por_tipo": por_tipo, "total_detectados": 5, "total_eventos": 6,
                 "falso_alarme_horas": 3, "horas_base": 300}
                for d in ("zscore", "lightgbm")
            ],
        },
        "baseline_fraca": {"criterio": "menos de 4 semanas", "semanas_completas_treino": 18},
    }


def gravar(pasta: Path, **sobrescritas: dict[str, Any]) -> Path:
    base = {ARQUIVO_RESUMO: resumo_json(), ARQUIVO_ALERTAS: alertas_json(), ARQUIVO_ECONOMIA: economia_json()}
    for nome, valor in sobrescritas.items():
        base[nome] = valor
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, dado in base.items():
        (pasta / nome).write_text(json.dumps(dado), encoding="utf-8")
    return pasta


def ambiente(pasta: Path) -> Ambiente:
    return montar(resultados_m3=ResultadosM3Json(pasta, "emp-a"))


@pytest.fixture
def amb_m3(tmp_path: Path) -> Ambiente:
    return ambiente(gravar(tmp_path / "m3"))


ROTAS = ["/modelos/resumo", "/alertas", "/economia"]


@pytest.mark.parametrize("rota", ROTAS)
def test_sem_chave_ou_chave_errada_e_401(amb_m3: Ambiente, rota: str) -> None:
    assert amb_m3.client.get(rota).status_code == 401
    assert amb_m3.client.get(rota, headers=bearer("x" * 40)).status_code == 401
    assert amb_m3.client.get(rota, headers={"X-Empresa-Id": "emp-a"}).status_code == 401


@pytest.mark.parametrize("rota", ROTAS)
def test_outra_empresa_recebe_vazio_nunca_o_dado_da_dona(amb_m3: Ambiente, rota: str) -> None:
    r = amb_m3.client.get(rota, headers=amb_m3.hb)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["disponivel"] is False
    assert "emp-a" not in r.text and "z1_" not in r.text
    dona = amb_m3.client.get(rota, headers=amb_m3.ha).json()
    assert dona["disponivel"] is True


def test_vazio_da_outra_empresa_por_rota(amb_m3: Ambiente) -> None:
    assert amb_m3.client.get("/alertas", headers=amb_m3.hb).json()["itens"] == []
    assert amb_m3.client.get("/alertas", headers=amb_m3.hb).json()["total"] == 0
    eco = amb_m3.client.get("/economia", headers=amb_m3.hb).json()
    assert eco["equipamentos"] == [] and eco["veredito"] is None and eco["valida_metodo_nao_economia_real"] is True
    resumo = amb_m3.client.get("/modelos/resumo", headers=amb_m3.hb).json()
    assert resumo["mae"] is None and resumo["shap"] is None and resumo["benchmark_sintetico"] is None


def test_outra_empresa_nao_ve_503_mesmo_sem_artefato(tmp_path: Path) -> None:
    amb = ambiente(tmp_path / "vazio")
    assert amb.client.get("/alertas", headers=amb.hb).status_code == 200
    assert amb.client.get("/alertas", headers=amb.ha).status_code == 503


@pytest.mark.parametrize("rota,nome", [("/modelos/resumo", ARQUIVO_RESUMO), ("/alertas", ARQUIVO_ALERTAS), ("/economia", ARQUIVO_ECONOMIA)])
def test_artefato_ausente_e_503(tmp_path: Path, rota: str, nome: str) -> None:
    pasta = gravar(tmp_path / "m3")
    (pasta / nome).rename(tmp_path / "removido.json")
    amb = ambiente(pasta)
    r = amb.client.get(rota, headers=amb.ha)
    assert r.status_code == 503
    assert nome in r.json()["detail"] and str(tmp_path) not in r.text


def test_resumo_503_se_faltar_o_artefato_de_alertas(tmp_path: Path) -> None:
    pasta = gravar(tmp_path / "m3")
    (pasta / ARQUIVO_ALERTAS).rename(tmp_path / "removido.json")
    amb = ambiente(pasta)
    assert amb.client.get("/modelos/resumo", headers=amb.ha).status_code == 503


def _quebrar_versao(d: dict[str, Any]) -> None:
    d["versao_esquema"] = 2


def _quebrar_campo_extra(d: dict[str, Any]) -> None:
    d["campo_novo"] = 1


def _quebrar_tipo(d: dict[str, Any]) -> None:
    d["sensor_id"] = 7


@pytest.mark.parametrize("quebra", [_quebrar_versao, _quebrar_campo_extra, _quebrar_tipo])
@pytest.mark.parametrize("rota,nome,fabrica", [
    ("/alertas", ARQUIVO_ALERTAS, alertas_json), ("/economia", ARQUIVO_ECONOMIA, economia_json),
    ("/modelos/resumo", ARQUIVO_RESUMO, resumo_json),
])
def test_artefato_fora_do_esquema_e_503(tmp_path: Path, rota: str, nome: str, fabrica: Any, quebra: Any) -> None:
    dado = fabrica()
    quebra(dado)
    amb = ambiente(gravar(tmp_path / "m3", **{nome: dado}))
    r = amb.client.get(rota, headers=amb.ha)
    assert r.status_code == 503 and "esquema" in r.json()["detail"]


def test_artefato_com_json_invalido_ou_nan_e_503(tmp_path: Path) -> None:
    pasta = gravar(tmp_path / "m3")
    (pasta / ARQUIVO_ALERTAS).write_text("{nao e json", encoding="utf-8")
    (pasta / ARQUIVO_ECONOMIA).write_text(json.dumps(economia_json()).replace('"tolerancia_pp": 3.0', '"tolerancia_pp": NaN'), encoding="utf-8")
    amb = ambiente(pasta)
    assert amb.client.get("/alertas", headers=amb.ha).status_code == 503
    assert amb.client.get("/economia", headers=amb.ha).status_code == 503


def test_alerta_zscore_com_shap_ou_lightgbm_sem_shap_e_recusado(tmp_path: Path) -> None:
    d = alertas_json()
    d["alertas"][0]["top_shap"] = [{"feature": "hora", "shap": 1.0}]
    amb = ambiente(gravar(tmp_path / "m3", **{ARQUIVO_ALERTAS: d}))
    assert amb.client.get("/alertas", headers=amb.ha).status_code == 503


def test_sem_path_traversal_link_para_fora_do_diretorio_e_indisponivel(tmp_path: Path) -> None:
    fora = tmp_path / "fora"
    gravar(fora)
    pasta = tmp_path / "m3"
    gravar(pasta)
    (pasta / ARQUIVO_ALERTAS).unlink()
    (pasta / ARQUIVO_ALERTAS).symlink_to(fora / ARQUIVO_ALERTAS)
    repo = ResultadosM3Json(pasta, "emp-a")
    with pytest.raises(ResultadosM3Indisponiveis, match="fora do diretorio"):
        repo.alertas("emp-a")
    assert repo.economia("emp-a") is not None


def test_nome_do_artefato_nao_vem_da_requisicao(amb_m3: Ambiente) -> None:
    r = amb_m3.client.get("/alertas", params={"equipamento": "../../etc/passwd"}, headers=amb_m3.ha)
    assert r.status_code == 200 and r.json()["total"] == 0


# ---------------------------------------------------------------- /alertas


def _alertas(amb: Ambiente, **params: Any) -> Any:
    return amb.client.get("/alertas", params=params, headers=amb.ha)


def test_alertas_formato_e_rotulo(amb_m3: Ambiente) -> None:
    corpo = _alertas(amb_m3).json()
    assert corpo["total"] == 5 and corpo["rotulo"] == "candidato, nao corroborado"
    assert corpo["limiar_z"] == 4.0 and corpo["aviso"]
    z, lgbm = corpo["itens"][0], corpo["itens"][1]
    assert z["rotulo"] == "candidato, nao corroborado" and z["timestamp"] == "2018-11-05T09:00:00-03:00"
    assert z["explicacao"] == {
        "z": -6.0, "esperado_kw": 2.0, "observado_kw": 0.5, "janela_baseline": {
            "inicio": "2018-07-01T00:00:00-03:00", "fim": "2018-11-04T00:00:00-03:00"}, "top_shap": None}
    assert [x["feature"] for x in lgbm["explicacao"]["top_shap"]] == ["kw_lag1", "hora", "kw_lag168"]


def test_alertas_filtros_equipamento_e_tipo(amb_m3: Ambiente) -> None:
    assert _alertas(amb_m3, equipamento="a").json()["total"] == 3
    assert _alertas(amb_m3, tipo="lightgbm").json()["total"] == 2
    assert _alertas(amb_m3, equipamento="b", tipo="zscore").json()["total"] == 1
    assert _alertas(amb_m3, equipamento="nao-existe").json()["total"] == 0
    assert _alertas(amb_m3, tipo="outro").status_code == 422


def test_alertas_filtro_de_ate_com_fuso(amb_m3: Ambiente) -> None:
    # 09:00 local (-03:00) == 12:00Z; `de` inclusivo, `ate` exclusivo
    assert _alertas(amb_m3, de="2018-11-05T09:00:00-03:00", ate="2018-11-06T09:00:00-03:00").json()["total"] == 2
    assert _alertas(amb_m3, de="2018-11-05T12:00:00+00:00", ate="2018-11-06T12:00:00+00:00").json()["total"] == 2
    assert _alertas(amb_m3, de="2018-11-05T09:00:01-03:00", ate="2018-11-06T09:00:01-03:00").json()["total"] == 2
    assert _alertas(amb_m3, de="2018-11-06T09:00:00-03:00").json()["total"] == 3


def test_alertas_data_sem_fuso_e_de_depois_de_ate_sao_422(amb_m3: Ambiente) -> None:
    assert _alertas(amb_m3, de="2018-11-05T09:00:00").status_code == 422
    assert _alertas(amb_m3, ate="2018-11-05").status_code == 422
    assert _alertas(amb_m3, de="2018-11-07T00:00:00-03:00", ate="2018-11-06T00:00:00-03:00").status_code == 422
    assert _alertas(amb_m3, de="2018-11-06T00:00:00-03:00", ate="2018-11-06T00:00:00-03:00").status_code == 422


@pytest.mark.parametrize("limite", [0, -1, 501, 100000])
def test_alertas_limite_fora_de_1_a_500_e_422(amb_m3: Ambiente, limite: int) -> None:
    assert _alertas(amb_m3, limite=limite).status_code == 422


@pytest.mark.parametrize("limite", [1, 500])
def test_alertas_limite_nas_bordas(amb_m3: Ambiente, limite: int) -> None:
    assert _alertas(amb_m3, limite=limite).status_code == 200


def test_alertas_offset_negativo_e_422(amb_m3: Ambiente) -> None:
    assert _alertas(amb_m3, offset=-1).status_code == 422


def test_alertas_paginacao_cobre_tudo_sem_repetir(amb_m3: Ambiente) -> None:
    vistos: list[str] = []
    offset: int | None = 0
    while offset is not None:
        pagina = _alertas(amb_m3, limite=2, offset=offset).json()
        assert pagina["total"] == 5 and len(pagina["itens"]) <= 2
        vistos += [f'{x["timestamp"]}|{x["equipamento"]}|{x["tipo"]}' for x in pagina["itens"]]
        offset = pagina["proximo_offset"]
    assert len(vistos) == 5 == len(set(vistos)) and vistos == sorted(vistos)
    assert _alertas(amb_m3, limite=2, offset=99).json()["itens"] == []


def test_alertas_422_nao_ecoa_valor(amb_m3: Ambiente) -> None:
    r = _alertas(amb_m3, limite="SEGREDO-123")
    assert r.status_code == 422 and "SEGREDO-123" not in r.text


# ---------------------------------------------------------------- /economia


def test_economia_veredito_derivado_dos_dados(amb_m3: Ambiente) -> None:
    corpo = amb_m3.client.get("/economia", headers=amb_m3.ha).json()
    assert corpo["valida_metodo_nao_economia_real"] is True
    v = corpo["veredito"]
    # erros: a=12 (fora), b=0.5 (dentro), c=-1 (dentro), d=n/d (fora)
    assert (v["equipamentos"], v["dentro_da_tolerancia"], v["tolerancia_atendida"]) == (4, 2, False)
    assert v["alvo_equipamento"] == "a" and v["alvo_injetado_pct"] == 15.0 and v["alvo_recuperado_pct"] == 27.0
    assert v["erro_abs_maximo_pp"] == 12.0 and "NAO atendida" in v["texto"] and "2 de 4" in v["texto"]
    linhas = {x["equipamento"]: x for x in corpo["equipamentos"]}
    assert linhas["b"]["dentro_da_tolerancia"] is True and linhas["b"]["injetado_pct"] == 15.0
    assert linhas["a"]["dentro_da_tolerancia"] is False and linhas["a"]["erro_pp"] == 12.0
    assert linhas["d"]["recuperado_pct"] is None and linhas["d"]["dentro_da_tolerancia"] is False
    assert linhas["c"]["baseline_fraca"] is True and linhas["c"]["tolerancia_pp"] == 3.0


def test_veredito_muda_quando_os_dados_mudam(tmp_path: Path) -> None:
    todos = economia_json({"a": 15.5, "b": 14.0, "c": 16.0}, alvo_dentro=True)
    amb = ambiente(gravar(tmp_path / "m3", **{ARQUIVO_ECONOMIA: todos}))
    v = amb.client.get("/economia", headers=amb.ha).json()["veredito"]
    assert v["tolerancia_atendida"] is True and v["dentro_da_tolerancia"] == 3 and "NAO" not in v["texto"]
    # alvo fora, mesmo com o resto dentro: nao atendida
    mix = economia_json({"a": 27.0, "b": 14.0, "c": 16.0}, alvo_dentro=False)
    amb2 = ambiente(gravar(tmp_path / "m3b", **{ARQUIVO_ECONOMIA: mix}))
    v2 = amb2.client.get("/economia", headers=amb2.ha).json()["veredito"]
    assert v2["tolerancia_atendida"] is False and v2["dentro_da_tolerancia"] == 2 and "2 de 3" in v2["texto"]


def test_economia_exige_equipamento_alvo_na_lista(tmp_path: Path) -> None:
    d = economia_json()
    d["reducao_sintetica"]["equipamento"] = "zzz"
    amb = ambiente(gravar(tmp_path / "m3", **{ARQUIVO_ECONOMIA: d}))
    assert amb.client.get("/economia", headers=amb.ha).status_code == 503


def test_economia_natureza_fixa_no_esquema(tmp_path: Path) -> None:
    d = economia_json()
    d["natureza"] = "economia_real"
    amb = ambiente(gravar(tmp_path / "m3", **{ARQUIVO_ECONOMIA: d}))
    assert amb.client.get("/economia", headers=amb.ha).status_code == 503


# ---------------------------------------------------------------- /modelos/resumo


def test_resumo_conteudo(amb_m3: Ambiente) -> None:
    c = amb_m3.client.get("/modelos/resumo", headers=amb_m3.ha).json()
    assert c["dados"]["equipamentos_modelados"] == 2 and c["dados"]["periodo"]["inicio"] == "2018-07-01T00:00:00-03:00"
    assert c["mae"]["baseline_sazonal_kw"] == 0.6 and c["mae"]["lightgbm_kw"] == 0.2
    assert c["mae"]["equipamentos_total"] == 2 and c["mae"]["equipamentos_lightgbm_melhor"] == 1
    assert "lag 1" in c["mae"]["ressalva_nowcast"] or "lag1" in c["mae"]["ressalva_nowcast"]
    assert c["shap"]["aviso_d7"] == {
        "disparado": True, "feature": "kw_lag1", "pct": 60.0, "limiar_pct": 50.0, "equipamentos_com_dominante": 1}
    b = c["benchmark_sintetico"]
    assert b["sintetico"] is True and "SINTETICO" in b["rotulo"]
    assert b["detectores"][0]["taxa_deteccao_pct"] == pytest.approx(100 * 5 / 6)
    assert b["detectores"][0]["por_tipo"][0]["taxa_deteccao_pct"] == 100.0
    assert b["detectores"][0]["taxa_falso_alarme_pct"] == pytest.approx(1.0)
    assert c["baseline_fraca"]["equipamentos"] == ["b", "c"]
    assert c["baseline_fraca"]["semanas_completas_treino"] == 18


def test_aviso_d7_derivado_nao_dispara_sem_feature_dominante(tmp_path: Path) -> None:
    r = resumo_json()
    r["shap"]["por_feature"] = [{"feature": "hora", "pct": 45.0}, {"feature": "kw_lag1", "pct": 45.0}]
    amb = ambiente(gravar(tmp_path / "m3", **{ARQUIVO_RESUMO: r}))
    aviso = amb.client.get("/modelos/resumo", headers=amb.ha).json()["shap"]["aviso_d7"]
    assert aviso["disparado"] is False


def test_baseline_fraca_vem_dos_dados(tmp_path: Path) -> None:
    a = alertas_json()
    e = economia_json()
    for x in a["alertas"]:
        x["baseline_fraca"] = False
    for x in e["equipamentos"]:
        x["baseline_fraca"] = False
    amb = ambiente(gravar(tmp_path / "m3", **{ARQUIVO_ALERTAS: a, ARQUIVO_ECONOMIA: e}))
    assert amb.client.get("/modelos/resumo", headers=amb.ha).json()["baseline_fraca"]["equipamentos"] == []


def test_leitura_nao_altera_artefatos_nem_aceita_escrita(amb_m3: Ambiente) -> None:
    for rota in ROTAS:
        assert amb_m3.client.post(rota, headers=amb_m3.ha, json={}).status_code == 405


def test_url_quote_do_mais_nao_quebra_o_fuso(amb_m3: Ambiente) -> None:
    de = quote("2018-11-05T09:00:00+00:00", safe="")
    r = amb_m3.client.get(f"/alertas?de={de}", headers=amb_m3.ha)
    assert r.status_code == 200 and r.json()["total"] == 5


# ---------------------------------------------------------------- dado real (gitignored)


@pytest.mark.skipif(not (DIR_REAL / ARQUIVO_RESUMO).exists(), reason="data/m3 nao gerado nesta maquina")
def test_artefatos_reais_do_m3_passam_no_esquema_e_o_veredito_bate_com_o_relatorio() -> None:
    amb = montar(resultados_m3=ResultadosM3Json(DIR_REAL, "emp-a"))
    eco = amb.client.get("/economia", headers=amb.ha).json()
    v = eco["veredito"]
    assert v["tolerancia_atendida"] is False and v["equipamentos"] == 19 and v["dentro_da_tolerancia"] == 7
    assert v["alvo_equipamento"] == "z1_Light" and round(v["alvo_recuperado_pct"], 2) == 27.18
    assert round(v["erro_abs_mediano_pp"], 2) == 6.71 and round(v["erro_abs_maximo_pp"], 2) == 18.90
    assert amb.client.get("/alertas", params={"limite": 500}, headers=amb.ha).json()["total"] == 214
    resumo = amb.client.get("/modelos/resumo", headers=amb.ha).json()
    assert resumo["mae"]["equipamentos_lightgbm_melhor"] == 19 and resumo["shap"]["aviso_d7"]["disparado"] is True
    assert resumo["baseline_fraca"]["equipamentos"] == []
