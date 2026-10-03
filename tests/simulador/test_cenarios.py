"""Os cenarios do dispositivo simulado contra a API real da plataforma, em processo."""

from __future__ import annotations

from datetime import timedelta

from ambiente_sim import (
    DEVICE,
    INICIO,
    NOME_AC,
    Ambiente,
    EnvioDuplicado,
    EnvioGravador,
    EnvioPerdeAck,
    FonteSintetica,
    esperado_local,
    minuto,
    montar,
)

from mapen_simulador.application.casos_de_uso import PedidoSimulacao, SimularSensor
from mapen_simulador.application.portas import EnvioLeituras
from mapen_simulador.domain.cenario import Cenario, Janela
from mapen_simulador.domain.dispositivo import ConfigDispositivo
from mapen_simulador.domain.eventos import TipoEvento
from mapen_simulador.domain.relatorio import RelatorioSimulacao
from mapen_simulador.domain.relogio import RelogioDispositivo
from mapen_simulador.infrastructure.api_http import EnvioLeiturasHttp

MINUTOS = 60


def _envio(amb: Ambiente) -> EnvioLeiturasHttp:
    return EnvioLeiturasHttp(amb.client, DEVICE, amb.token)


def _rodar(
    envio: EnvioLeituras, cenario: Cenario, config: ConfigDispositivo | None = None, minutos: int = MINUTOS
) -> RelatorioSimulacao:
    pedido = PedidoSimulacao(
        config or ConfigDispositivo(DEVICE), NOME_AC, INICIO, timedelta(minutes=minutos), cenario
    )
    return SimularSensor(FonteSintetica(), envio).executar(pedido)


def _esperado_serie(n: int) -> list[object]:
    return list(esperado_local([minuto(i) for i in range(n)]))


def test_1_leituras_estaveis_chegam_completas() -> None:
    amb = montar()
    relatorio = _rodar(_envio(amb), Cenario())
    assert relatorio.amostras_registradas == MINUTOS
    assert relatorio.amostras_confirmadas == MINUTOS
    assert relatorio.pendentes_no_fim == 0
    assert relatorio.lacunas == ()
    assert relatorio.eventos == ()
    assert amb.timestamps_gravados() == _esperado_serie(MINUTOS)


def test_2_wifi_fora_10_min_buferiza_e_entrega_em_lote_com_hora_do_dispositivo() -> None:
    amb = montar()
    gravador = EnvioGravador(_envio(amb))
    cenario = Cenario(janelas_wifi=(Janela(minuto(20), minuto(30)),))
    relatorio = _rodar(gravador, cenario)
    assert amb.timestamps_gravados() == _esperado_serie(MINUTOS)  # sem buraco
    assert amb.total_gravado() == amb.distintos_gravados() == MINUTOS
    assert relatorio.lacunas == ()
    assert relatorio.pendentes_no_fim == 0
    # Os 10 minutos sem conexao sairam juntos, num unico lote, assim que a conexao voltou.
    maior = max(gravador.lotes, key=lambda lote: len(lote.amostras))
    assert [a.ts for a in maior.amostras[:10]] == [minuto(i) for i in range(20, 30)]
    assert len(maior.amostras) == 11  # os 10 guardados mais a amostra do minuto 30
    (evento,) = relatorio.eventos
    assert evento.tipo is TipoEvento.FALHA_CONEXAO
    assert evento.duracao_s == 600.0


def test_2b_reenvio_do_lote_nao_duplica_nem_cria_buraco() -> None:
    amb = montar()
    duplicado = EnvioDuplicado(_envio(amb))
    cenario = Cenario(janelas_wifi=(Janela(minuto(20), minuto(30)),))
    _rodar(duplicado, cenario)
    assert duplicado.reenvios > 0
    assert amb.total_gravado() == amb.distintos_gravados() == MINUTOS
    assert amb.timestamps_gravados() == _esperado_serie(MINUTOS)


def test_2c_ack_perdido_dispositivo_reenvia_o_mesmo_lote_sem_duplicar() -> None:
    amb = montar()
    perde = EnvioPerdeAck(_envio(amb))
    gravador = EnvioGravador(perde)
    relatorio = _rodar(gravador, Cenario(janelas_wifi=(Janela(minuto(20), minuto(30)),)))
    assert perde.acks_perdidos > 0
    assert relatorio.envios_falhos == perde.acks_perdidos
    ids = [lote.id for lote in gravador.lotes]
    assert len(ids) > len(set(ids))  # o mesmo id foi reenviado
    assert relatorio.amostras_confirmadas == MINUTOS
    assert amb.total_gravado() == amb.distintos_gravados() == MINUTOS


def test_2d_o_horario_gravado_e_o_do_relogio_do_dispositivo_com_deriva() -> None:
    amb = montar()
    deriva = 1000.0  # 1000 ppm: o RTC adianta 3,6 s por hora
    config = ConfigDispositivo(DEVICE, deriva_ppm=deriva)
    _rodar(_envio(amb), Cenario(), config)
    rtc = RelogioDispositivo(INICIO, deriva)
    assert amb.timestamps_gravados() == esperado_local([rtc.ler(minuto(i)) for i in range(MINUTOS)])
    assert amb.timestamps_gravados() != _esperado_serie(MINUTOS)


def test_3_queda_de_energia_dentro_da_autonomia() -> None:
    amb = montar()
    gravador = EnvioGravador(_envio(amb))
    deriva = 500.0
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(35)),), autonomia=timedelta(minutes=30))
    relatorio = _rodar(gravador, cenario, ConfigDispositivo(DEVICE, deriva_ppm=deriva))
    rtc = RelogioDispositivo(INICIO, deriva)
    ultimo_suspiro, queda = relatorio.eventos
    assert ultimo_suspiro.tipo is TipoEvento.ULTIMO_SUSPIRO
    assert ultimo_suspiro.inicio == rtc.ler(minuto(20))
    assert queda.tipo is TipoEvento.QUEDA_ENERGIA
    assert queda.inicio == ultimo_suspiro.inicio
    assert queda.duracao_s == (rtc.ler(minuto(35)) - rtc.ler(minuto(20))).total_seconds()
    assert 900.0 < queda.duracao_s < 901.0  # 900 s reais, vistos pelo RTC com deriva
    assert not queda.bateria_esgotada
    # A bateria manteve o registro: sem buraco e tudo entregue depois da volta da energia.
    assert relatorio.lacunas == ()
    assert relatorio.amostras_registradas == relatorio.amostras_confirmadas == MINUTOS
    durante = [rtc.ler(minuto(i)) for i in range(20, 35)]
    lotes_com_queda = [lote for lote in gravador.lotes if durante[0] in {a.ts for a in lote.amostras}]
    assert len(lotes_com_queda) == 1  # um unico lote, enviado so depois da volta
    assert {a.ts for a in lotes_com_queda[0].amostras} >= set(durante)
    assert amb.timestamps_gravados() == esperado_local([rtc.ler(minuto(i)) for i in range(MINUTOS)])


def test_4_queda_maior_que_a_autonomia_mostra_o_buraco_real_sem_interpolar() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(50)),), autonomia=timedelta(minutes=10))
    relatorio = _rodar(_envio(amb), cenario)
    assert relatorio.amostras_registradas == 40  # 20 antes + 10 na bateria + 10 depois
    assert relatorio.amostras_confirmadas == 40
    (lacuna,) = relatorio.lacunas
    assert lacuna.inicio == minuto(29) and lacuna.fim == minuto(50)
    assert lacuna.amostras_faltantes == 20
    gravados = amb.timestamps_gravados()
    assert len(gravados) == 40
    assert not [t for t in gravados if esperado_local([minuto(29)])[0] < t < esperado_local([minuto(50)])[0]]
    queda = relatorio.eventos[-1]
    assert queda.bateria_esgotada
    assert queda.duracao_s == 1800.0  # o RTC sobreviveu: a duracao real da queda e conhecida


def test_4b_rtc_que_nao_sobrevive_a_bateria_zerada_nao_inventa_duracao() -> None:
    amb = montar()
    cenario = Cenario(janelas_energia=(Janela(minuto(20), minuto(50)),), autonomia=timedelta(minutes=10))
    relatorio = _rodar(_envio(amb), cenario, ConfigDispositivo(DEVICE, rtc_sobrevive_a_bateria_zerada=False))
    queda = relatorio.eventos[-1]
    assert queda.bateria_esgotada and queda.fim is None and queda.duracao_s is None
    assert relatorio.eventos[0].tipo is TipoEvento.ULTIMO_SUSPIRO  # o inicio foi gravado antes de a bateria acabar


def test_buffer_circular_perde_o_mais_antigo_e_conta() -> None:
    amb = montar()
    config = ConfigDispositivo(DEVICE, capacidade_buffer=5)
    relatorio = _rodar(_envio(amb), Cenario(janelas_wifi=(Janela(minuto(10), minuto(30)),)), config)
    # 20 min offline mais a amostra do minuto da volta (gravada antes do envio): 21 amostras, so 5 cabem.
    assert relatorio.amostras_perdidas_overflow == 16
    assert relatorio.amostras_confirmadas == relatorio.amostras_registradas - 16
    assert amb.total_gravado() == MINUTOS - 16
    ts = amb.timestamps_gravados()
    assert esperado_local([minuto(10)])[0] not in ts  # as mais antigas foram as perdidas
    assert esperado_local([minuto(30)])[0] in ts
