"""Autenticacao por chave de API por empresa e por token de dispositivo; hashes apenas; rotacao; CLI."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ambiente import Ambiente, bearer, montar
from mapen_plataforma.domain.comando import EstadoRele
from mapen_plataforma.domain.credenciais import hash_segredo, segredo_confere
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.demo import EMPRESA_DEMO, EMPRESA_OUTRA, SENSOR_CU_BEMS
from mapen_plataforma.interface import cli
from mapen_plataforma.interface.api.composicao import montar_app_demo

ENDPOINTS_GET = ["/unidades", "/sensores", "/equipamentos", "/regras", "/eventos", "/configuracao"]


@pytest.mark.parametrize("caminho", ENDPOINTS_GET)
def test_sem_credencial_e_401(amb: Ambiente, caminho: str) -> None:
    resposta = amb.client.get(caminho)
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "cabecalho",
    ["Bearer", "Bearer ", "Basic abc", "Bearer chave-errada", "bearer " + "x" * 5000, "x"],
)
def test_credencial_malformada_ou_errada_e_401_sem_dado_do_tenant(amb: Ambiente, cabecalho: str) -> None:
    resposta = amb.client.get("/sensores", headers={"Authorization": cabecalho})
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "nao autenticado"}
    assert "emp-a" not in resposta.text


def test_credencial_com_byte_nao_ascii_e_401(amb: Ambiente) -> None:
    resposta = amb.client.get("/sensores", headers={b"Authorization": "Bearer é".encode("latin-1")})
    assert resposta.status_code == 401


def test_header_x_empresa_id_nao_autentica_mais(amb: Ambiente) -> None:
    assert amb.client.get("/sensores", headers={"X-Empresa-Id": "emp-b"}).status_code == 401
    # nem mistura com a chave de outra empresa: manda a empresa da chave
    h = {**amb.ha, "X-Empresa-Id": "emp-b"}
    assert {s["id"] for s in amb.client.get("/sensores", headers=h).json()} == {"sa"}


def test_chave_de_uma_empresa_nao_ve_a_outra(amb: Ambiente) -> None:
    assert {s["id"] for s in amb.client.get("/sensores", headers=amb.ha).json()} == {"sa"}
    assert {s["id"] for s in amb.client.get("/sensores", headers=amb.hb).json()} == {"sb"}


def test_resposta_401_e_igual_para_chave_inexistente_e_para_chave_vazia(amb: Ambiente) -> None:
    a = amb.client.get("/sensores", headers=bearer("a" * 43))
    b = amb.client.get("/sensores")
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_token_de_dispositivo_nao_abre_endpoints_da_empresa(amb: Ambiente) -> None:
    assert amb.client.get("/sensores", headers=bearer(amb.tokens["sa"])).status_code == 401


def test_chave_da_empresa_nao_ingere_leitura(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-07T10:00:00-03:00", "kwh": 1.0}]}
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=amb.ha).status_code == 401
    assert amb.client.post("/sensores/sa/leituras", json=corpo).status_code == 401
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=bearer(amb.tokens["sa"])).json() == {
        "gravadas": 1
    }


def test_ingestao_de_sensor_inexistente_tambem_e_401_sem_oraculo(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": []}
    r1 = amb.client.post("/sensores/nao-existe/leituras", json=corpo, headers=bearer(amb.tokens["sa"]))
    r2 = amb.client.post("/sensores/sb/leituras", json=corpo, headers=bearer(amb.tokens["sa"]))
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()


def test_autenticacao_vem_antes_da_validacao_do_corpo(amb: Ambiente) -> None:
    assert amb.client.post("/sensores/sa/leituras", json={"lixo": 1}).status_code == 401
    assert amb.client.post("/unidades", json={"lixo": 1}).status_code == 401


def test_banco_guarda_so_hash_nunca_o_segredo(amb: Ambiente) -> None:
    segredos = [*amb.chaves_api.values(), *amb.tokens.values(), *(k.hex() for k in amb.chaves_comando.values())]
    dump = " ".join(
        str(linha)
        for tabela in ("credencial_empresa", "credencial_dispositivo")
        for linha in amb.banco.consultar(f"SELECT * FROM {tabela}")
    )
    for segredo in segredos:
        assert segredo not in dump
    guardados = {str(r[0]) for r in amb.banco.consultar("SELECT hash_chave FROM credencial_empresa")}
    assert hashlib.sha256(amb.chaves_api["emp-a"].encode()).hexdigest() in guardados
    assert segredo_confere(amb.chaves_api["emp-a"], hash_segredo(amb.chaves_api["emp-a"]))
    assert not segredo_confere("outra", hash_segredo(amb.chaves_api["emp-a"]))


def test_chaves_sao_urlsafe_de_32_bytes_e_unicas(amb: Ambiente) -> None:
    for chave in (*amb.chaves_api.values(), *amb.tokens.values()):
        assert len(chave) == 43  # token_urlsafe(32)
    todas = [*amb.chaves_api.values(), *amb.tokens.values()]
    assert len(set(todas)) == len(todas)


def test_cada_dispositivo_tem_sua_propria_chave_de_comando(amb: Ambiente) -> None:
    assert amb.chaves_comando["sa"] != amb.chaves_comando["sb"]


def test_rotacao_invalida_token_e_chave_de_comando_antigos(amb: Ambiente) -> None:
    antigo_token, antiga_chave = amb.tokens["sa"], amb.chaves_comando["sa"]
    resposta = amb.client.post("/sensores/sa/credenciais", headers=amb.ha)
    assert resposta.status_code == 200
    novo = resposta.json()
    corpo: dict[str, Any] = {"leituras": []}
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=bearer(antigo_token)).status_code == 401
    assert amb.client.post(
        "/sensores/sa/leituras", json=corpo, headers=bearer(novo["token_dispositivo"])
    ).status_code == 200
    pedido = {"equipamento_id": "eq-ac", "comando": amb.comando(chave=antiga_chave)}
    assert amb.client.post("/desligamentos", json=pedido, headers=amb.ha).json()["motivo"] == "assinatura_invalida"
    pedido = {
        "equipamento_id": "eq-ac",
        "comando": amb.comando(nonce="depois", chave=bytes.fromhex(novo["chave_comando"])),
    }
    assert amb.client.post("/desligamentos", json=pedido, headers=amb.ha).status_code == 200
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.DESLIGADO


def test_rotacao_de_sensor_de_outra_empresa_e_404(amb: Ambiente) -> None:
    assert amb.client.post("/sensores/sb/credenciais", headers=amb.ha).status_code == 404


def test_criar_sensor_gera_credenciais_proprias_uma_vez(amb: Ambiente) -> None:
    resposta = amb.client.post("/sensores", json={"unidade_id": "u-emp-a", "nome": "novo"}, headers=amb.ha)
    assert resposta.status_code == 201
    dados = resposta.json()
    token = dados["credenciais"]["token_dispositivo"]
    corpo: dict[str, Any] = {"leituras": []}
    assert amb.client.post(f"/sensores/{dados['id']}/leituras", json=corpo, headers=bearer(token)).status_code == 200
    assert "credenciais" not in amb.client.get("/sensores", headers=amb.ha).json()[0]


def test_cli_cria_empresa_e_imprime_a_chave_uma_vez(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = tmp_path / "boot.duckdb"
    assert cli.main(["criar-empresa", "--nome", "Clinica X", "--db", str(db)]) == 0
    saida = capsys.readouterr().out
    campos = dict(linha.split("=", 1) for linha in saida.strip().splitlines())
    chave, empresa_id = campos["chave_api"], campos["empresa_id"]
    banco = BancoDuckDB(db)
    linhas = banco.consultar("SELECT hash_chave, empresa_id, principal FROM credencial_empresa")
    assert linhas == [(hash_segredo(chave), empresa_id, "admin")]
    assert chave not in " ".join(str(c) for t in ("empresa", "credencial_empresa") for c in banco.consultar(f"SELECT * FROM {t}"))
    banco.conexao.close()


def test_cli_nao_loga_a_chave(tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    cli.main(["criar-empresa", "--nome", "Y", "--db", str(tmp_path / "b.duckdb")])
    chave = dict(linha.split("=", 1) for linha in capsys.readouterr().out.strip().splitlines())["chave_api"]
    assert chave not in caplog.text


def test_cli_recusa_nome_vazio(tmp_path: Path) -> None:
    assert cli.main(["criar-empresa", "--nome", "  ", "--db", str(tmp_path / "c.duckdb")]) == 2


def test_chave_do_ambiente_precisa_ter_32_caracteres(tmp_path: Path) -> None:
    from mapen_plataforma.application.casos_de_uso import ProvisionarEmpresa
    from mapen_plataforma.domain.entidades import ErroDominio
    from mapen_plataforma.infrastructure.repositorios import CredenciaisEmpresaDuckDB, EmpresaDuckDB
    from mapen_plataforma.infrastructure.servicos import GeradorSequencial

    banco = BancoDuckDB()
    caso = ProvisionarEmpresa(EmpresaDuckDB(banco), CredenciaisEmpresaDuckDB(banco), GeradorSequencial())
    with pytest.raises(ErroDominio):
        caso.executar("E", chave="curta")


def test_demo_cria_chaves_proprias_e_reemite_a_cada_partida(tmp_path: Path) -> None:
    caminho = tmp_path / "demo.duckdb"
    banco = BancoDuckDB(caminho)
    banco.executar(
        "INSERT INTO leitura VALUES (?, ?, ?, 1, 1, 1, false)", [SENSOR_CU_BEMS, "z1_AC1", datetime(2018, 8, 1)]
    )
    banco.conexao.close()
    primeira = montar_app_demo(caminho, b"m" * 32)
    segredos = {s.empresa_id: s for s in primeira.segredos}
    assert segredos[EMPRESA_DEMO].chave_api != segredos[EMPRESA_OUTRA].chave_api
    assert segredos[EMPRESA_DEMO].dispositivo.token != segredos[EMPRESA_OUTRA].dispositivo.token
    assert len(segredos[EMPRESA_DEMO].chave_api) == 43
    cliente = TestClient(primeira.app)
    assert cliente.get("/sensores", headers=bearer(segredos[EMPRESA_DEMO].chave_api)).status_code == 200
    assert cliente.get("/sensores").status_code == 401
    segunda = montar_app_demo(caminho, b"m" * 32, {EMPRESA_DEMO: "f" * 40})
    assert segunda.segredos[0].chave_api == "f" * 40
    novo = TestClient(segunda.app)
    assert novo.get("/sensores", headers=bearer("f" * 40)).status_code == 200
    assert novo.get("/sensores", headers=bearer(segredos[EMPRESA_DEMO].chave_api)).status_code == 401
