"""Comando assinado emitido pelo simulador contra a API real da plataforma (regras de aceite e recusa)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from ambiente_sim import DEVICE, EMPRESA, EQ_AC, EQ_AC2, EQ_CRITICO, Ambiente, montar

from mapen_plataforma.domain.comando import Acao
from mapen_simulador.application.casos_de_uso import EmitirComando
from mapen_simulador.application.portas import RespostaComando
from mapen_simulador.domain.comando import construir_comando
from mapen_simulador.domain.erros import ErroSimulador
from mapen_simulador.infrastructure.api_http import EnvioComandoHttp
from mapen_simulador.infrastructure.chaves import ChaveDerivada, ChaveFixa
from mapen_simulador.infrastructure.nonces import NonceUuid


def _emissor(amb: Ambiente) -> EmitirComando:
    chaves = ChaveDerivada(b"segredo-mestre-do-simulador-0123456789", {DEVICE: amb.sal})
    return EmitirComando(chaves, amb.relogio, NonceUuid(), EnvioComandoHttp(amb.client, amb.chave_api))


def _emitir(
    amb: Ambiente,
    equipamento: str = EQ_AC,
    acao: Acao = Acao.DESLIGAR,
    validade_s: float = 30.0,
    nonce: str | None = None,
    emitido_em: datetime | None = None,
) -> RespostaComando:
    resultado = _emissor(amb).executar(
        DEVICE, EMPRESA, equipamento, acao, validade_s=validade_s, nonce=nonce, emitido_em=emitido_em
    )
    return resultado.resposta


def test_a_chave_derivada_pelo_simulador_e_a_do_provisionamento() -> None:
    amb = montar()
    chaves = ChaveDerivada(b"segredo-mestre-do-simulador-0123456789", {DEVICE: amb.sal})
    assert chaves.chave(DEVICE) == amb.chave_comando == ChaveFixa({DEVICE: amb.chave_comando.hex()}).chave(DEVICE)


def test_5_comando_aceito_com_flag_ligada_e_equipamento_nao_critico() -> None:
    amb = montar()
    resposta = _emitir(amb)
    assert resposta == RespostaComando(True, 200, None)


def test_5_ligar_e_aceito_mesmo_com_flag_desligada() -> None:
    amb = montar(habilitado=False)
    assert _emitir(amb, acao=Acao.LIGAR).aceito


def test_5_recusado_para_equipamento_critico() -> None:
    amb = montar()
    assert _emitir(amb, EQ_CRITICO) == RespostaComando(False, 403, "equipamento_critico")


def test_5_recusado_com_comando_expirado() -> None:
    amb = montar()
    emitido = amb.relogio.agora() - timedelta(seconds=100)
    assert _emitir(amb, emitido_em=emitido, validade_s=30.0) == RespostaComando(False, 403, "validade_vencida")


def test_5_recusado_com_nonce_repetido() -> None:
    amb = montar()
    assert _emitir(amb, nonce="n-fixo").aceito
    assert _emitir(amb, nonce="n-fixo") == RespostaComando(False, 403, "nonce_repetido")


def test_5_recusado_com_equipamento_id_adulterado() -> None:
    amb = montar()
    emissor = _emissor(amb)
    comando = emissor.assinar(DEVICE, EMPRESA, EQ_AC, Acao.DESLIGAR)  # assinado para EQ_AC, nao critico
    resposta = EnvioComandoHttp(amb.client, amb.chave_api).enviar(comando, EQ_AC2, "simulador", None)  # enviado como EQ_AC2
    assert resposta == RespostaComando(False, 403, "assinatura_invalida")


def test_5_recusado_com_flag_desligada() -> None:
    amb = montar(habilitado=False)
    assert _emitir(amb) == RespostaComando(False, 403, "desligamento_remoto_desabilitado")


def test_5_chave_errada_e_assinatura_invalida() -> None:
    amb = montar()
    emissor = EmitirComando(
        ChaveFixa({DEVICE: "00" * 32}), amb.relogio, NonceUuid(), EnvioComandoHttp(amb.client, amb.chave_api)
    )
    assert emissor.executar(DEVICE, EMPRESA, EQ_AC, Acao.DESLIGAR).resposta.motivo == "assinatura_invalida"


@pytest.mark.parametrize("validade_s", [0.0, -1.0, 61.0])
def test_validade_fora_de_0_a_60_s_nem_e_assinada(validade_s: float) -> None:
    amb = montar()
    with pytest.raises(ErroSimulador):
        construir_comando(amb.chave_comando, DEVICE, EMPRESA, EQ_AC, Acao.DESLIGAR, "n", amb.relogio.agora(), validade_s)
