"""Caso de uso SolicitarDesligamento via API: evento sempre gravado, nonce, rele simulado."""

from __future__ import annotations

from typing import Any

from ambiente import CHAVE_A, HA, Ambiente
from mapen_plataforma.domain.comando import Acao, EstadoRele


def _pedir(amb: Ambiente, equipamento: str = "eq-ac", autorizado: str | None = "joao", **cmd: Any) -> Any:
    corpo: dict[str, Any] = {"equipamento_id": equipamento, "comando": amb.comando(**cmd), "origem": "teste"}
    if autorizado is not None:
        corpo["autorizado_por"] = autorizado
    return amb.client.post("/desligamentos", json=corpo, headers=HA)


def _eventos(amb: Ambiente) -> list[dict[str, Any]]:
    resposta = amb.client.get("/eventos", headers=HA)
    assert resposta.status_code == 200
    dados: list[dict[str, Any]] = resposta.json()
    return dados


def test_desligamento_valido_executa_e_gera_evento_com_origem_e_regra(amb: Ambiente) -> None:
    regra = amb.client.post(
        "/regras",
        json={"equipamento_id": "eq-ac", "cron": "0 22 * * 1-5", "autorizado_por": "joao"},
        headers=HA,
    ).json()
    resposta = amb.client.post(
        "/desligamentos",
        json={"equipamento_id": "eq-ac", "comando": amb.comando(), "autorizado_por": "joao",
              "origem": "regra", "regra_id": regra["id"]},
        headers=HA,
    )
    assert resposta.status_code == 200 and resposta.json()["aceito"] is True
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.DESLIGADO
    eventos = _eventos(amb)
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "desligamento_executado"
    assert eventos[0]["origem"] == "regra" and eventos[0]["regra_id"] == regra["id"]
    assert eventos[0]["autorizado_por"] == "joao"


def test_rejeicoes_sempre_geram_evento_e_nao_acionam_o_rele(amb: Ambiente) -> None:
    casos: list[tuple[Any, str]] = [
        (_pedir(amb, equipamento="eq-crit", nonce="a"), "equipamento_critico"),
        (_pedir(amb, autorizado=None, nonce="b"), "sem_autorizacao"),
        (_pedir(amb, nonce="c", chave=b"errada"), "assinatura_invalida"),
        (_pedir(amb, nonce="d", validade_s=-1), "validade_vencida"),
    ]
    for resposta, motivo in casos:
        assert resposta.status_code == 403
        assert resposta.json()["motivo"] == motivo
    eventos = _eventos(amb)
    assert len(eventos) == len(casos)
    assert {e["tipo"] for e in eventos} == {"comando_rejeitado"}
    assert {e["payload"]["motivo"] for e in eventos} == {m for _, m in casos}
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_nonce_repetido_e_rejeitado_na_segunda_vez(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="mesmo").status_code == 200
    segunda = _pedir(amb, nonce="mesmo")
    assert segunda.status_code == 403 and segunda.json()["motivo"] == "nonce_repetido"
    assert [e["tipo"] for e in reversed(_eventos(amb))] == ["desligamento_executado", "comando_rejeitado"]


def test_assinatura_invalida_nao_queima_o_nonce(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="x", chave=b"errada").status_code == 403
    assert _pedir(amb, nonce="x", chave=CHAVE_A).status_code == 200


def test_flag_global_desligada_rejeita_e_registra(amb_flag_off: Ambiente) -> None:
    resposta = _pedir(amb_flag_off)
    assert resposta.status_code == 403
    assert resposta.json()["motivo"] == "desligamento_remoto_desabilitado"
    assert amb_flag_off.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO
    assert len(_eventos(amb_flag_off)) == 1


def test_religar_apos_desligar(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="1").status_code == 200
    assert _pedir(amb, nonce="2", acao=Acao.LIGAR).status_code == 200
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_regra_para_equipamento_critico_e_recusada(amb: Ambiente) -> None:
    resposta = amb.client.post(
        "/regras", json={"equipamento_id": "eq-crit", "cron": "0 22 * * *", "autorizado_por": "joao"}, headers=HA
    )
    assert resposta.status_code == 422


def test_regra_sem_autorizado_por_e_recusada(amb: Ambiente) -> None:
    resposta = amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *", "autorizado_por": " "}, headers=HA
    )
    assert resposta.status_code == 422


def test_alterar_regra_e_listar(amb: Ambiente) -> None:
    regra = amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *", "autorizado_por": "joao"}, headers=HA
    ).json()
    assert amb.client.patch(f"/regras/{regra['id']}", json={"ativo": False}, headers=HA).status_code == 200
    listadas = amb.client.get("/regras", headers=HA).json()
    assert [r["ativo"] for r in listadas] == [False]


def test_reinicio_do_atuador_volta_energizado(amb: Ambiente) -> None:
    from mapen_plataforma.infrastructure.servicos import AtuadorSimulado

    assert _pedir(amb).status_code == 200
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.DESLIGADO
    assert AtuadorSimulado().estado("sa", "AC1") is EstadoRele.ENERGIZADO
