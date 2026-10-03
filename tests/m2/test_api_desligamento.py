"""Caso de uso SolicitarDesligamento via API: eventos em todo caminho, nonce, rele simulado."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from ambiente import Ambiente, montar
from mapen_plataforma.application.portas import ErroAtuador, EventoRepo
from mapen_plataforma.domain.comando import Acao, EstadoRele
from mapen_plataforma.domain.entidades import Evento
from mapen_plataforma.infrastructure.servicos import AtuadorSimulado


def _pedir(amb: Ambiente, equipamento: str = "eq-ac", headers: dict[str, str] | None = None, **cmd: Any) -> Any:
    corpo: dict[str, Any] = {"equipamento_id": equipamento, "comando": amb.comando(**cmd), "origem": "teste"}
    return amb.client.post("/desligamentos", json=corpo, headers=headers or amb.ha)


def _eventos(amb: Ambiente, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    resposta = amb.client.get("/eventos", headers=headers or amb.ha)
    assert resposta.status_code == 200
    dados: list[dict[str, Any]] = resposta.json()
    return dados


def _tipos(amb: Ambiente) -> list[str]:
    return [e["tipo"] for e in reversed(_eventos(amb))]


def test_desligamento_valido_executa_e_gera_intencao_e_resultado(amb: Ambiente) -> None:
    regra = amb.client.post("/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * 1-5"}, headers=amb.ha).json()
    resposta = amb.client.post(
        "/desligamentos",
        json={"equipamento_id": "eq-ac", "comando": amb.comando(), "origem": "regra", "regra_id": regra["id"]},
        headers=amb.ha,
    )
    assert resposta.status_code == 200 and resposta.json()["aceito"] is True
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.DESLIGADO
    assert _tipos(amb) == ["comando_recebido", "desligamento_executado"]
    resultado = _eventos(amb)[0]
    assert resultado["origem"] == "regra" and resultado["regra_id"] == regra["id"]
    assert resultado["autorizado_por"] == "ana"  # nome do principal, nao do corpo
    assert resultado["payload"]["intencao_id"] == _eventos(amb)[1]["id"]
    assert resposta.json()["evento_id"] == resultado["id"]


def test_rejeicoes_sempre_geram_intencao_e_resultado_e_nao_acionam_o_rele(amb: Ambiente) -> None:
    casos: list[tuple[Any, str]] = [
        (_pedir(amb, equipamento="eq-crit", nonce="a", equipamento_id="eq-crit"), "equipamento_critico"),
        (_pedir(amb, nonce="c", chave=b"errada"), "assinatura_invalida"),
        (_pedir(amb, nonce="d", validade_s=-30, emitido_s=-60), "validade_vencida"),
        (_pedir(amb, nonce="e", validade_s=3600), "ttl_excessivo"),
        (_pedir(amb, nonce="f", device_id="sb"), "dispositivo_divergente"),
    ]
    for resposta, motivo in casos:
        assert resposta.status_code == 403
        assert resposta.json()["motivo"] == motivo
    eventos = _eventos(amb)
    assert len(eventos) == 2 * len(casos)
    rejeitados = [e for e in eventos if e["tipo"] == "comando_rejeitado"]
    assert {e["payload"]["motivo"] for e in rejeitados} == {m for _, m in casos}
    assert {e["tipo"] for e in eventos} == {"comando_recebido", "comando_rejeitado"}
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_equipamento_desconhecido_gera_evento_e_404(amb: Ambiente) -> None:
    resposta = _pedir(amb, equipamento="nao-existe")
    assert resposta.status_code == 404 and resposta.json()["motivo"] == "equipamento_desconhecido"
    assert _tipos(amb) == ["comando_recebido", "comando_rejeitado"]
    assert _eventos(amb)[0]["payload"]["equipamento_solicitado"] == "nao-existe"


def test_sonda_entre_empresas_gera_evento_so_na_empresa_do_chamador(amb: Ambiente) -> None:
    resposta = _pedir(amb, equipamento="eq-b")  # equipamento da empresa B, chave da A
    assert resposta.status_code == 404
    assert len(_eventos(amb)) == 2
    assert _eventos(amb, amb.hb) == []
    assert amb.atuador.estado("sb", "AC1") is EstadoRele.ENERGIZADO


def test_nonce_repetido_e_rejeitado_na_segunda_vez(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="mesmo").status_code == 200
    segunda = _pedir(amb, nonce="mesmo")
    assert segunda.status_code == 403 and segunda.json()["motivo"] == "nonce_repetido"
    assert _tipos(amb)[-1] == "comando_rejeitado"


def test_assinatura_invalida_nao_queima_o_nonce(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="x", chave=b"errada").status_code == 403
    assert _pedir(amb, nonce="x").status_code == 200


def test_ttl_excessivo_nao_queima_o_nonce(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="y", validade_s=3600).status_code == 403
    assert _pedir(amb, nonce="y").status_code == 200


def test_comando_assinado_para_outro_equipamento_nao_vale(amb: Ambiente) -> None:
    """A assinatura amarra o equipamento: reaproveitar o comando de eq-ac contra eq-crit nao passa."""
    corpo = {"equipamento_id": "eq-crit", "comando": amb.comando(equipamento_id="eq-ac"), "origem": "t"}
    resposta = amb.client.post("/desligamentos", json=corpo, headers=amb.ha)
    assert resposta.status_code == 403 and resposta.json()["motivo"] == "assinatura_invalida"


def test_flag_por_empresa_desligada_rejeita_e_registra(amb_flag_off: Ambiente) -> None:
    resposta = _pedir(amb_flag_off)
    assert resposta.status_code == 403
    assert resposta.json()["motivo"] == "desligamento_remoto_desabilitado"
    assert amb_flag_off.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO
    assert len(_eventos(amb_flag_off)) == 2


def test_flag_e_por_empresa(amb: Ambiente) -> None:
    amb.habilitar("emp-b", False)
    assert amb.client.get("/configuracao", headers=amb.ha).json() == {"desligamento_remoto_habilitado": True}
    assert amb.client.get("/configuracao", headers=amb.hb).json() == {"desligamento_remoto_habilitado": False}
    assert _pedir(amb).status_code == 200


def test_configuracao_padrao_e_desligada_e_put_registra_evento_com_o_principal() -> None:
    amb = montar(habilitado=False)
    assert amb.client.get("/configuracao", headers=amb.ha).json() == {"desligamento_remoto_habilitado": False}
    resposta = amb.client.put("/configuracao", json={"desligamento_remoto_habilitado": True}, headers=amb.ha)
    assert resposta.status_code == 200 and resposta.json() == {"desligamento_remoto_habilitado": True}
    assert amb.client.get("/configuracao", headers=amb.ha).json() == {"desligamento_remoto_habilitado": True}
    evento = _eventos(amb)[0]
    assert evento["tipo"] == "configuracao_alterada" and evento["autorizado_por"] == "ana"
    assert evento["payload"] == {
        "desligamento_remoto_habilitado_antes": "false",
        "desligamento_remoto_habilitado": "true",
    }
    assert amb.client.get("/configuracao", headers=amb.hb).json() == {"desligamento_remoto_habilitado": False}
    assert _pedir(amb).status_code == 200


def test_regra_inexistente_inativa_ou_de_outro_equipamento_e_rejeitada_com_evento(amb: Ambiente) -> None:
    from mapen_plataforma.domain.entidades import Equipamento
    from mapen_plataforma.infrastructure.repositorios import EquipamentoDuckDB

    EquipamentoDuckDB(amb.banco).adicionar(Equipamento("eq-2", "emp-a", "sa", "AC2", False))
    ativa = amb.client.post("/regras", json={"equipamento_id": "eq-2", "cron": "0 22 * * *"}, headers=amb.ha).json()
    inativa = amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *", "ativo": False}, headers=amb.ha
    ).json()
    regra_b = amb.client.post("/regras", json={"equipamento_id": "eq-b", "cron": "0 22 * * *"}, headers=amb.hb).json()
    for i, regra_id in enumerate(["nao-existe", ativa["id"], inativa["id"], regra_b["id"]]):
        corpo = {"equipamento_id": "eq-ac", "comando": amb.comando(nonce=f"r{i}"), "regra_id": regra_id}
        resposta = amb.client.post("/desligamentos", json=corpo, headers=amb.ha)
        assert resposta.status_code == 403 and resposta.json()["motivo"] == "regra_invalida", regra_id
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO
    assert len([e for e in _eventos(amb) if e["tipo"] == "comando_rejeitado"]) == 4


def test_religar_apos_desligar(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="1").status_code == 200
    assert _pedir(amb, nonce="2", acao=Acao.LIGAR).status_code == 200
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_regra_para_equipamento_critico_e_recusada(amb: Ambiente) -> None:
    resposta = amb.client.post("/regras", json={"equipamento_id": "eq-crit", "cron": "0 22 * * *"}, headers=amb.ha)
    assert resposta.status_code == 422


def test_regra_ignora_autorizado_por_do_corpo_e_usa_o_principal(amb: Ambiente) -> None:
    com_campo = amb.client.post(
        "/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *", "autorizado_por": "fantasma"},
        headers=amb.ha,
    )
    assert com_campo.status_code == 422
    regra = amb.client.post("/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *"}, headers=amb.ha).json()
    assert regra["autorizado_por"] == "ana"


def test_autorizado_por_no_corpo_do_desligamento_e_recusado(amb: Ambiente) -> None:
    corpo = {"equipamento_id": "eq-ac", "comando": amb.comando(), "autorizado_por": "fantasma"}
    assert amb.client.post("/desligamentos", json=corpo, headers=amb.ha).status_code == 422
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_alterar_regra_e_listar(amb: Ambiente) -> None:
    regra = amb.client.post("/regras", json={"equipamento_id": "eq-ac", "cron": "0 22 * * *"}, headers=amb.ha).json()
    assert amb.client.patch(f"/regras/{regra['id']}", json={"ativo": False}, headers=amb.ha).status_code == 200
    assert [r["ativo"] for r in amb.client.get("/regras", headers=amb.ha).json()] == [False]


def test_reinicio_do_atuador_volta_energizado(amb: Ambiente) -> None:
    assert _pedir(amb).status_code == 200
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.DESLIGADO
    assert AtuadorSimulado().estado("sa", "AC1") is EstadoRele.ENERGIZADO


class _AtuadorEspia(AtuadorSimulado):
    def __init__(self) -> None:
        super().__init__()
        self.chamadas = 0

    def aplicar(self, device_id: str, equipamento_id: str, acao: Acao) -> None:
        self.chamadas += 1
        super().aplicar(device_id, equipamento_id, acao)


class _AtuadorQuebrado(AtuadorSimulado):
    def aplicar(self, device_id: str, equipamento_id: str, acao: Acao) -> None:
        raise ErroAtuador("rele sem resposta")


class _EventosQueFalham:
    def adicionar(self, evento: Evento) -> None:
        raise RuntimeError("disco cheio")

    def listar(self, empresa_id: str, limite: int) -> list[Evento]:
        return []


class _EventosComLog:
    def __init__(self, interno: EventoRepo, log: list[str]) -> None:
        self._interno, self._log = interno, log

    def adicionar(self, evento: Evento) -> None:
        self._log.append(evento.tipo.value)
        self._interno.adicionar(evento)

    def listar(self, empresa_id: str, limite: int) -> list[Evento]:
        return self._interno.listar(empresa_id, limite)


def test_se_a_intencao_nao_for_gravada_o_atuador_nao_e_chamado() -> None:
    espia = _AtuadorEspia()
    amb = montar(atuador=espia)
    amb.servicos.desligar = replace(amb.servicos.desligar, eventos=_EventosQueFalham())
    with pytest.raises(RuntimeError, match="disco cheio"):
        _pedir(amb)
    assert espia.chamadas == 0
    assert amb.atuador.estado("sa", "AC1") is EstadoRele.ENERGIZADO


def test_ordem_intencao_atuador_resultado() -> None:
    log: list[str] = []

    class Espia(AtuadorSimulado):
        def aplicar(self, device_id: str, equipamento_id: str, acao: Acao) -> None:
            log.append("atuador")
            super().aplicar(device_id, equipamento_id, acao)

    amb = montar(atuador=Espia())
    amb.servicos.desligar = replace(
        amb.servicos.desligar, eventos=_EventosComLog(amb.servicos.desligar.eventos, log)
    )
    assert _pedir(amb).status_code == 200
    assert log == ["comando_recebido", "atuador", "desligamento_executado"]


def test_falha_do_atuador_vira_evento_e_resposta_403() -> None:
    amb = montar(atuador=_AtuadorQuebrado())
    resposta = _pedir(amb)
    assert resposta.status_code == 403 and resposta.json()["motivo"] == "falha_atuador"
    assert _tipos(amb) == ["comando_recebido", "falha_conexao"]


@pytest.mark.parametrize(
    "mexer",
    [
        {"nonce": "outro"},
        {"acao": "ligar"},
        {"device_id": "sb"},
        {"validade": "2026-10-05T12:00:59+00:00"},
        {"emitido_em": "2026-10-05T11:59:59+00:00"},
    ],
)
def test_guarda_adulterar_qualquer_campo_assinado_e_rejeitado(amb: Ambiente, mexer: dict[str, str]) -> None:
    """Guarda do caminho feliz: o comando intacto passa, e mexer em qualquer campo assinado nao passa."""
    assert _pedir(amb, nonce="intacto").status_code == 200
    comando = amb.comando(nonce="ok")
    comando.update(mexer)
    corpo = {"equipamento_id": "eq-ac", "comando": comando}
    assert amb.client.post("/desligamentos", json=corpo, headers=amb.ha).status_code == 403
