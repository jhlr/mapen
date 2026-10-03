"""Validacao de entrada: limites, tamanhos, datas sem fuso, ids do servidor."""

from __future__ import annotations

from typing import Any

import pytest

from ambiente import Ambiente, bearer

P = "inicio=2026-10-05T00:00:00-03:00&fim=2026-10-06T00:00:00-03:00"


@pytest.mark.parametrize("limite", [0, -1, 501, 100000])
def test_limite_de_eventos_fora_de_1_a_500(amb: Ambiente, limite: int) -> None:
    assert amb.client.get(f"/eventos?limite={limite}", headers=amb.ha).status_code == 422


@pytest.mark.parametrize("limite", [1, 500])
def test_limite_de_eventos_nas_bordas(amb: Ambiente, limite: int) -> None:
    assert amb.client.get(f"/eventos?limite={limite}", headers=amb.ha).status_code == 200


@pytest.mark.parametrize("n", [0, -3, 101, 100000])
def test_n_do_ranking_fora_de_1_a_100(amb: Ambiente, n: int) -> None:
    assert amb.client.get(f"/sensores/sa/ranking?{P}&n={n}", headers=amb.ha).status_code == 422


@pytest.mark.parametrize("n", [1, 100])
def test_n_do_ranking_nas_bordas(amb: Ambiente, n: int) -> None:
    assert amb.client.get(f"/sensores/sa/ranking?{P}&n={n}", headers=amb.ha).status_code == 200


@pytest.mark.parametrize("campo", ["nome"])
def test_nome_gigante_ou_vazio(amb: Ambiente, campo: str) -> None:
    assert amb.client.post("/unidades", json={campo: "x" * 121}, headers=amb.ha).status_code == 422
    assert amb.client.post("/unidades", json={campo: ""}, headers=amb.ha).status_code == 422
    assert amb.client.post("/unidades", json={campo: "x" * 120}, headers=amb.ha).status_code == 201
    assert amb.client.post("/unidades", json={campo: "   "}, headers=amb.ha).status_code == 422


def test_limites_de_nonce_origem_e_device(amb: Ambiente) -> None:
    def tentar(**mexer: Any) -> int:
        comando = amb.comando(nonce="ok1")
        comando.update({k: v for k, v in mexer.items() if k != "origem"})
        corpo: dict[str, Any] = {"equipamento_id": "eq-ac", "comando": comando}
        if "origem" in mexer:
            corpo["origem"] = mexer["origem"]
        return amb.client.post("/desligamentos", json=corpo, headers=amb.ha).status_code

    assert tentar(nonce="n" * 129) == 422
    assert tentar(nonce="") == 422
    assert tentar(origem="o" * 65) == 422
    assert tentar(origem="") == 422
    assert tentar(device_id="d" * 129) == 422


def test_assinatura_fora_do_padrao_e_422(amb: Ambiente) -> None:
    for lixo in ("é" * 64, "A" * 64, "0" * 63, "0" * 65, "g" * 64, ""):
        comando = amb.comando()
        comando["assinatura"] = lixo
        corpo = {"equipamento_id": "eq-ac", "comando": comando}
        assert amb.client.post("/desligamentos", json=corpo, headers=amb.ha).status_code == 422, lixo


@pytest.mark.parametrize("campo", ["validade", "emitido_em"])
def test_datas_do_comando_sem_fuso_sao_recusadas(amb: Ambiente, campo: str) -> None:
    comando = amb.comando()
    comando[campo] = "2026-10-05T12:00:30"
    corpo = {"equipamento_id": "eq-ac", "comando": comando}
    assert amb.client.post("/desligamentos", json=corpo, headers=amb.ha).status_code == 422


@pytest.mark.parametrize(
    "caminho",
    [
        "/sensores/sa/custo?inicio=2026-10-05T00:00:00&fim=2026-10-06T00:00:00-03:00",
        "/sensores/sa/ranking?inicio=2026-10-05T00:00:00-03:00&fim=2026-10-06T00:00:00",
        "/consumo/horario?sensor_id=sa&inicio=2026-10-05T00:00:00&fim=2026-10-06T00:00:00",
    ],
)
def test_periodos_sem_fuso_sao_recusados(amb: Ambiente, caminho: str) -> None:
    assert amb.client.get(caminho, headers=amb.ha).status_code == 422


def test_leitura_sem_fuso_e_recusada_e_nada_e_gravado(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-07T10:00:00", "kwh": 1.0}]}
    antes = amb.banco.consultar("SELECT count(*) FROM leitura")[0][0]
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=bearer(amb.tokens["sa"])).status_code == 422
    assert amb.banco.consultar("SELECT count(*) FROM leitura")[0][0] == antes


def test_lote_de_leituras_limitado_a_5000(amb: Ambiente) -> None:
    def lote(n: int) -> dict[str, Any]:
        return {"leituras": [{"equipamento": "AC1", "ts": f"2030-01-01T00:00:00+00:00", "kwh": 1.0}] * n}

    h = bearer(amb.tokens["sa"])
    assert amb.client.post("/sensores/sa/leituras", json=lote(5001), headers=h).status_code == 422
    assert amb.client.post("/sensores/sa/leituras", json=lote(5000), headers=h).status_code == 200


def test_leitura_com_numero_nao_finito_e_recusada(amb: Ambiente) -> None:
    corpo = '{"leituras": [{"equipamento": "AC1", "ts": "2030-01-01T00:00:00+00:00", "kwh": NaN}]}'
    resposta = amb.client.post(
        "/sensores/sa/leituras", content=corpo, headers={**bearer(amb.tokens["sa"]), "Content-Type": "application/json"}
    )
    assert resposta.status_code == 422


def test_cliente_nao_escolhe_id_de_sensor(amb: Ambiente) -> None:
    corpo = {"unidade_id": "u-emp-a", "nome": "x", "id": "sb"}
    assert amb.client.post("/sensores", json=corpo, headers=amb.ha).status_code == 422


def test_ids_de_sensor_sao_gerados_pelo_servidor_e_unicos(amb: Ambiente) -> None:
    ids = {
        amb.client.post("/sensores", json={"unidade_id": "u-emp-a", "nome": "x"}, headers=amb.ha).json()["id"]
        for _ in range(5)
    }
    assert len(ids) == 5 and ids.isdisjoint({"sa", "sb"})


def test_equipamento_exige_critico_explicito(amb: Ambiente) -> None:
    sem = amb.client.post("/equipamentos", json={"sensor_id": "sa", "nome": "novo"}, headers=amb.ha)
    assert sem.status_code == 422
    com = amb.client.post("/equipamentos", json={"sensor_id": "sa", "nome": "novo", "critico": False}, headers=amb.ha)
    assert com.status_code == 201 and com.json()["critico"] is False
    critico = amb.client.post("/equipamentos", json={"sensor_id": "sa", "nome": "n2", "critico": True}, headers=amb.ha)
    assert critico.json()["critico"] is True


def test_equipamento_ignora_id_do_cliente(amb: Ambiente) -> None:
    corpo = {"sensor_id": "sa", "nome": "novo", "critico": True, "id": "eq-ac"}
    assert amb.client.post("/equipamentos", json=corpo, headers=amb.ha).status_code == 422
