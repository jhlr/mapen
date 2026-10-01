"""Isolamento multi-tenant: recurso de outra empresa nunca e devolvido nem comandavel."""

from __future__ import annotations

from typing import Any

import pytest

from ambiente import HA, HB, Ambiente
from mapen_plataforma.domain.comando import EstadoRele

INICIO = "2026-10-05T00:00:00"
FIM = "2026-10-06T00:00:00"


def _contar(amb: Ambiente) -> int:
    total = amb.banco.consultar("SELECT count(*) FROM leitura WHERE sensor_id = 'sb'")[0][0]
    assert isinstance(total, int)
    return total


def test_listagens_so_trazem_a_propria_empresa(amb: Ambiente) -> None:
    sensores_b = {s["id"] for s in amb.client.get("/sensores", headers=HB).json()}
    assert sensores_b == {"sb"}
    equipamentos_b = {e["id"] for e in amb.client.get("/equipamentos", headers=HB).json()}
    assert equipamentos_b == {"eq-b"}
    equipamentos_a = {e["id"] for e in amb.client.get("/equipamentos", headers=HA).json()}
    assert equipamentos_a == {"eq-ac", "eq-crit"}


@pytest.mark.parametrize(
    "caminho",
    [
        "/sensores/sb/consumo-agora",
        f"/sensores/sb/custo?inicio={INICIO}&fim={FIM}",
        f"/sensores/sb/ranking?inicio={INICIO}&fim={FIM}",
    ],
)
def test_sensor_de_outra_empresa_e_404(amb: Ambiente, caminho: str) -> None:
    assert amb.client.get(caminho, headers=HA).status_code == 404
    assert amb.client.get(caminho, headers=HB).status_code == 200


def test_nao_grava_leitura_em_sensor_de_outra_empresa(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {"leituras": [{"equipamento": "AC1", "ts": "2026-10-06T00:00:00", "kwh": 1.0}]}
    assert amb.client.post("/sensores/sb/leituras", json=corpo, headers=HA).status_code == 404
    antes = _contar(amb)
    assert amb.client.post("/sensores/sb/leituras", json=corpo, headers=HB).status_code == 200
    assert _contar(amb) == antes + 1


def test_equipamento_de_outra_empresa_nao_e_comandavel(amb: Ambiente) -> None:
    # Mesmo com comando validamente assinado para o dispositivo da empresa B.
    from ambiente import CHAVE_B

    corpo = {
        "equipamento_id": "eq-b",
        "comando": amb.comando(device_id="sb", chave=CHAVE_B),
        "autorizado_por": "joao",
    }
    assert amb.client.post("/desligamentos", json=corpo, headers=HA).status_code == 404
    assert amb.atuador.estado("sb", "AC1") is EstadoRele.ENERGIZADO
    assert amb.client.get("/eventos", headers=HA).json() == []
    assert amb.client.get("/eventos", headers=HB).json() == []


def test_regra_e_evento_nao_vazam_entre_empresas(amb: Ambiente) -> None:
    regra = amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *", "autorizado_por": "joao"}, headers=HA
    ).json()
    assert amb.client.get("/regras", headers=HB).json() == []
    assert amb.client.patch(f"/regras/{regra['id']}", json={"ativo": False}, headers=HB).status_code == 404
    assert amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *", "autorizado_por": "x"}, headers=HB
    ).status_code == 404


def test_comando_do_dispositivo_de_outra_empresa_contra_o_proprio_equipamento_e_rejeitado(amb: Ambiente) -> None:
    from ambiente import CHAVE_B

    corpo = {
        "equipamento_id": "eq-ac",
        "comando": amb.comando(device_id="sb", chave=CHAVE_B),
        "autorizado_por": "joao",
    }
    resposta = amb.client.post("/desligamentos", json=corpo, headers=HA)
    assert resposta.status_code == 403 and resposta.json()["motivo"] == "dispositivo_divergente"


def test_cadastro_nao_aceita_sensor_em_unidade_de_outra_empresa(amb: Ambiente) -> None:
    assert amb.client.post("/sensores", json={"unidade_id": "u-emp-b", "nome": "x"}, headers=HA).status_code == 404


def test_header_ausente_ou_empresa_desconhecida(amb: Ambiente) -> None:
    assert amb.client.get("/sensores").status_code == 422
    assert amb.client.get("/sensores", headers={"X-Empresa-Id": "nao-existe"}).status_code == 403
