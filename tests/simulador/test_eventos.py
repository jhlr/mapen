"""Eventos do dispositivo (ultimo suspiro, queda de energia, falha de conexao) chegando a plataforma real."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from ambiente_sim import DEVICE, INICIO, NOME_AC, Ambiente, FonteSintetica, minuto, montar

from mapen_plataforma.infrastructure.servicos import RelogioFixo
from mapen_simulador.application.casos_de_uso import PedidoSimulacao, SimularSensor
from mapen_simulador.application.portas import EnvioEventos
from mapen_simulador.domain.cenario import Cenario, Janela
from mapen_simulador.domain.dispositivo import ConfigDispositivo
from mapen_simulador.domain.eventos import EventoDispositivo
from mapen_simulador.domain.relatorio import RelatorioSimulacao
from mapen_simulador.domain.relogio import RelogioDispositivo
from mapen_simulador.infrastructure.api_http import EnvioEventosHttp, EnvioLeiturasHttp

MINUTOS = 60


class EnvioEventosFalhaNoInicio:
    """Os `falhas` primeiros envios nunca chegam ao servidor (rede ruim); depois o envio real funciona."""

    def __init__(self, interno: EnvioEventos, falhas: int) -> None:
        self._interno = interno
        self._falhas = falhas
        self.tentativas = 0

    def enviar(self, eventos: Sequence[EventoDispositivo]) -> bool:
        self.tentativas += 1
        if self.tentativas <= self._falhas:
            return False
        return self._interno.enviar(eventos)


class EnvioEventosPerdeAck:
    """O servidor grava os eventos, mas o ack se perde na primeira tentativa."""

    def __init__(self, interno: EnvioEventos) -> None:
        self._interno = interno
        self.tentativas = 0

    def enviar(self, eventos: Sequence[EventoDispositivo]) -> bool:
        self.tentativas += 1
        ok = self._interno.enviar(eventos)
        return ok and self.tentativas > 1


def _rodar(
    amb: Ambiente, cenario: Cenario, envio_eventos: EnvioEventos | None, config: ConfigDispositivo | None = None
) -> RelatorioSimulacao:
    pedido = PedidoSimulacao(
        config or ConfigDispositivo(DEVICE), NOME_AC, INICIO, timedelta(minutes=MINUTOS), cenario
    )
    caso = SimularSensor(FonteSintetica(), EnvioLeiturasHttp(amb.client, DEVICE, amb.token), envio_eventos)
    return caso.executar(pedido)


def _http(amb: Ambiente) -> EnvioEventosHttp:
    return EnvioEventosHttp(amb.client, DEVICE, amb.token)


def _log(amb: Ambiente) -> list[dict[str, Any]]:
    resposta = amb.client.get("/eventos", headers={"Authorization": f"Bearer {amb.chave_api}"})
    assert resposta.status_code == 200
    lista: list[dict[str, Any]] = resposta.json()
    return lista


def test_queda_de_energia_chega_com_o_relogio_do_dispositivo() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    deriva = 500.0
    relatorio = _rodar(amb, cenario, _http(amb), ConfigDispositivo(DEVICE, deriva_ppm=deriva))
    rtc = RelogioDispositivo(INICIO, deriva)
    por_tipo = {e["tipo"]: e for e in _log(amb)}
    assert set(por_tipo) == {"ultimo_suspiro", "queda_energia"}
    suspiro, queda = por_tipo["ultimo_suspiro"], por_tipo["queda_energia"]
    assert suspiro["origem"] == "dispositivo" and suspiro["sensor_id"] == DEVICE and "fim" not in suspiro["payload"]
    assert datetime.fromisoformat(suspiro["ts"]) == rtc.ler(minuto(20))  # 20 min de relogio com deriva de 500 ppm
    durante = (rtc.ler(minuto(35)) - rtc.ler(minuto(20))).total_seconds()
    assert float(queda["payload"]["duracao_s"]) == durante and 900.0 < durante < 901.0
    assert queda["payload"]["bateria_esgotada"] == "false"
    assert relatorio.eventos_confirmados == 2 and relatorio.eventos_nao_confirmados == 0


def test_eventos_so_saem_quando_ha_conexao_um_unico_envio_apos_a_volta_da_energia() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    envio = EnvioEventosFalhaNoInicio(_http(amb), falhas=0)
    _rodar(amb, cenario, envio)
    assert envio.tentativas == 1  # o ultimo suspiro nao saiu durante a queda: so junto com a queda, na volta


def test_falha_de_conexao_chega_com_inicio_e_fim_do_relogio_do_dispositivo() -> None:
    amb = montar()
    cenario = Cenario(janelas_wifi=(Janela(minuto(10), minuto(20)),))
    relatorio = _rodar(amb, cenario, _http(amb))
    (evento,) = [e for e in _log(amb) if e["tipo"] == "falha_conexao"]
    assert float(evento["payload"]["duracao_s"]) == 600.0 and "fim" in evento["payload"]
    assert relatorio.eventos_confirmados == 1


def test_bateria_esgotada_sem_rtc_nao_inventa_duracao() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(50)),), autonomia=timedelta(minutes=10))
    _rodar(amb, cenario, _http(amb), ConfigDispositivo(DEVICE, rtc_sobrevive_a_bateria_zerada=False))
    queda = next(e for e in _log(amb) if e["tipo"] == "queda_energia")
    assert queda["payload"]["bateria_esgotada"] == "true"
    assert "duracao_s" not in queda["payload"] and "fim" not in queda["payload"]


def test_envio_que_falha_e_tentado_de_novo_ate_chegar() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    envio = EnvioEventosFalhaNoInicio(_http(amb), falhas=3)
    relatorio = _rodar(amb, cenario, envio)
    assert envio.tentativas == 4  # tres falhas (um por tick) e a quarta passa
    assert sorted(e["tipo"] for e in _log(amb)) == ["queda_energia", "ultimo_suspiro"]
    assert relatorio.eventos_confirmados == 2 and relatorio.eventos_nao_confirmados == 0


def test_ack_perdido_reenvia_sem_duplicar_no_servidor() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    envio = EnvioEventosPerdeAck(_http(amb))
    relatorio = _rodar(amb, cenario, envio)
    assert envio.tentativas == 2  # a segunda tentativa reenviou o mesmo lote
    assert len(_log(amb)) == 2
    assert relatorio.eventos_confirmados == 2


def test_sem_envio_de_eventos_nada_e_enviado_e_o_relatorio_nao_conta_confirmacao() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    relatorio = _rodar(amb, cenario, None)
    assert _log(amb) == [] and len(relatorio.eventos) == 2
    assert relatorio.eventos_confirmados == 0 and relatorio.eventos_nao_confirmados == 0


def test_evento_que_nunca_chega_fica_como_nao_confirmado_no_relatorio() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    envio = EnvioEventosFalhaNoInicio(_http(amb), falhas=10_000)
    relatorio = _rodar(amb, cenario, envio)
    assert _log(amb) == []
    assert relatorio.eventos_confirmados == 0 and relatorio.eventos_nao_confirmados == 2


def test_relogio_do_servidor_nao_e_usado_para_o_instante_do_evento() -> None:
    amb = montar()
    amb.relogio.avancar(3600)  # a plataforma recebe uma hora depois da simulacao; o ts continua sendo o do RTC
    assert isinstance(amb.relogio, RelogioFixo)
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    _rodar(amb, cenario, _http(amb))
    suspiro = next(e for e in _log(amb) if e["tipo"] == "ultimo_suspiro")
    assert suspiro["ts"].startswith("2026-10-05T13:20:00")  # 10:20 Recife = 13:20 UTC
    assert suspiro["payload"]["recebido_em"].startswith("2026-10-05T14:00:00")
