"""Isolamento multi-tenant: recurso de outra empresa nunca e devolvido nem comandavel."""

from __future__ import annotations

from typing import Any

import pytest

from ambiente import Ambiente, bearer
from mapen_plataforma.domain.comando import EstadoRele

INICIO = "2026-10-05T00:00:00-03:00"
FIM = "2026-10-06T00:00:00-03:00"


def _contar(amb: Ambiente) -> int:
    total = amb.banco.consultar("SELECT count(*) FROM leitura WHERE sensor_id = 'sb'")[0][0]
    assert isinstance(total, int)
    return total


def test_listagens_so_trazem_a_propria_empresa(amb: Ambiente) -> None:
    assert {s["id"] for s in amb.client.get("/sensores", headers=amb.hb).json()} == {"sb"}
    assert {e["id"] for e in amb.client.get("/equipamentos", headers=amb.hb).json()} == {"eq-b"}
    assert {e["id"] for e in amb.client.get("/equipamentos", headers=amb.ha).json()} == {"eq-ac", "eq-crit"}


@pytest.mark.parametrize(
    "caminho",
    [
        "/sensores/sb/consumo-agora",
        f"/sensores/sb/custo?inicio={INICIO}&fim={FIM}",
        f"/sensores/sb/ranking?inicio={INICIO}&fim={FIM}",
        f"/consumo/horario?sensor_id=sb&inicio={INICIO}&fim={FIM}",
    ],
)
def test_sensor_de_outra_empresa_e_404(amb: Ambiente, caminho: str) -> None:
    assert amb.client.get(caminho, headers=amb.ha).status_code == 404
    assert amb.client.get(caminho, headers=amb.hb).status_code == 200


def test_nao_grava_leitura_em_sensor_de_outra_empresa(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-06T00:00:00-03:00", "kwh": 1.0}]}
    # A chave da empresa A nao autentica ingestao; o token do dispositivo de A nao vale para o sensor de B.
    assert amb.client.post("/sensores/sb/leituras", json=corpo, headers=amb.ha).status_code == 401
    assert amb.client.post("/sensores/sb/leituras", json=corpo, headers=bearer(amb.tokens["sa"])).status_code == 401
    antes = _contar(amb)
    assert amb.client.post("/sensores/sb/leituras", json=corpo, headers=bearer(amb.tokens["sb"])).status_code == 200
    assert _contar(amb) == antes + 1


def test_equipamento_de_outra_empresa_nao_e_comandavel(amb: Ambiente) -> None:
    corpo = {
        "equipamento_id": "eq-b",
        "comando": amb.comando(device_id="sb", empresa_id="emp-b", equipamento_id="eq-b"),
    }
    resposta = amb.client.post("/desligamentos", json=corpo, headers=amb.ha)
    assert resposta.status_code == 404
    assert amb.atuador.estado("sb", "AC1") is EstadoRele.ENERGIZADO
    assert amb.client.get("/eventos", headers=amb.hb).json() == []


def test_chave_de_b_nao_comanda_equipamento_de_a(amb: Ambiente) -> None:
    corpo = {"equipamento_id": "eq-ac", "comando": amb.comando()}
    assert amb.client.post("/desligamentos", json=corpo, headers=amb.hb).status_code == 404
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_regra_e_evento_nao_vazam_entre_empresas(amb: Ambiente) -> None:
    regra = amb.client.post("/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *"}, headers=amb.ha).json()
    assert amb.client.get("/regras", headers=amb.hb).json() == []
    assert amb.client.patch(f"/regras/{regra['id']}", json={"ativo": False}, headers=amb.hb).status_code == 404
    assert amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *"}, headers=amb.hb
    ).status_code == 404


def test_comando_do_dispositivo_de_outra_empresa_contra_o_proprio_equipamento_e_rejeitado(amb: Ambiente) -> None:
    corpo = {"equipamento_id": "eq-ac", "comando": amb.comando(device_id="sb")}
    resposta = amb.client.post("/desligamentos", json=corpo, headers=amb.ha)
    assert resposta.status_code == 403 and resposta.json()["motivo"] == "dispositivo_divergente"


def test_cadastro_nao_aceita_sensor_em_unidade_de_outra_empresa(amb: Ambiente) -> None:
    assert amb.client.post("/sensores", json={"unidade_id": "u-emp-b", "nome": "x"}, headers=amb.ha).status_code == 404
    assert amb.client.post(
        "/equipamentos", json={"sensor_id": "sb", "nome": "x", "critico": True}, headers=amb.ha
    ).status_code == 404
