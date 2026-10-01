"""Leitor do M1 (CU-BEMS em DuckDB), arquivo de cenario e regras de entrada do dispositivo."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest
from ambiente_sim import DEVICE, INICIO, minuto

from mapen_aconselhamento.infrastructure.duckdb_leituras import LeiturasDuckDB, conectar, inserir_leituras
from mapen_plataforma.domain.tempo import para_local_ingenuo
from mapen_simulador.application.casos_de_uso import PedidoSimulacao, SimularSensor
from mapen_simulador.domain.amostras import LoteLeituras
from mapen_simulador.domain.cenario import Cenario, Janela
from mapen_simulador.domain.dispositivo import ConfigDispositivo
from mapen_simulador.domain.erros import ErroSimulador
from mapen_simulador.infrastructure.cenario_json import ler_cenario
from mapen_simulador.infrastructure.serie_m1 import FonteSerieM1


class _Coletor:
    def __init__(self) -> None:
        self.lotes: list[LoteLeituras] = []

    def enviar(self, lote: LoteLeituras) -> bool:
        self.lotes.append(lote)
        return True


def _banco_m1() -> LeiturasDuckDB:
    """Mesmo esquema do M1: 30 min de uma zona, com um minuto ausente (NaN)."""
    con = conectar(":memory:")
    indice = pd.date_range(para_local_ingenuo(INICIO), periods=30, freq="1min")
    valores = [0.6 + 0.01 * i for i in range(30)]
    valores[7] = float("nan")
    inserir_leituras(con, pd.DataFrame({"z1_AC1": valores}, index=indice), "predio", "1min", 1000.0, 0, "erro")
    return LeiturasDuckDB(con)


def test_serie_do_leitor_do_m1_vira_potencia_em_w_e_lacuna_sem_interpolar() -> None:
    serie = FonteSerieM1(_banco_m1(), "predio").carregar("z1_AC1", INICIO, timedelta(minutes=30))
    assert serie.passo == timedelta(minutes=1)
    assert serie.valores_w[0] == pytest.approx(600.0)
    assert serie.valores_w[1] == pytest.approx(610.0)
    assert serie.valores_w[7] is None


def test_simular_a_partir_do_leitor_do_m1_nao_inventa_a_amostra_ausente() -> None:
    coletor = _Coletor()
    pedido = PedidoSimulacao(ConfigDispositivo(DEVICE), "z1_AC1", INICIO, timedelta(minutes=30), Cenario())
    relatorio = SimularSensor(FonteSerieM1(_banco_m1(), "predio"), coletor).executar(pedido)
    assert relatorio.amostras_registradas == 29
    (lacuna,) = relatorio.lacunas
    assert lacuna.inicio == minuto(6) and lacuna.fim == minuto(8) and lacuna.amostras_faltantes == 1


def test_serie_inexistente_e_erro() -> None:
    with pytest.raises(ErroSimulador):
        FonteSerieM1(_banco_m1(), "predio").carregar("z9_AC9", INICIO, timedelta(minutes=30))


def test_reiniciar_em_move_a_serie_para_outro_eixo_de_tempo() -> None:
    coletor = _Coletor()
    novo = minuto(60 * 24 * 365)
    pedido = PedidoSimulacao(
        ConfigDispositivo(DEVICE), "z1_AC1", INICIO, timedelta(minutes=30), Cenario(), reiniciar_em=novo
    )
    SimularSensor(FonteSerieM1(_banco_m1(), "predio"), coletor).executar(pedido)
    assert coletor.lotes[0].amostras[0].ts == novo


def test_janela_menor_que_um_passo_e_recusada() -> None:
    pedido = PedidoSimulacao(
        ConfigDispositivo(DEVICE), "z1_AC1", INICIO, timedelta(minutes=30),
        Cenario(janelas_wifi=(Janela(minuto(5), minuto(5) + timedelta(seconds=10)),)),
    )
    with pytest.raises(ErroSimulador):
        SimularSensor(FonteSerieM1(_banco_m1(), "predio"), _Coletor()).executar(pedido)


def test_arquivo_de_cenario(tmp_path: Path) -> None:
    arquivo = tmp_path / "cenario.json"
    arquivo.write_text(json.dumps({
        "bateria_min": 15, "deriva_ppm": 20,
        "wifi": [{"inicio_min": 10, "duracao_min": 10}], "energia": [{"inicio_min": 60, "duracao_min": 30}],
    }))
    relativo = ler_cenario(arquivo)
    cenario = relativo.a_partir_de(INICIO)
    assert relativo.deriva_ppm == 20.0
    assert cenario.autonomia == timedelta(minutes=15)
    assert cenario.janelas_wifi == (Janela(minuto(10), minuto(20)),)
    assert cenario.janelas_energia == (Janela(minuto(60), minuto(90)),)


def test_arquivo_de_cenario_malformado_e_erro(tmp_path: Path) -> None:
    arquivo = tmp_path / "ruim.json"
    arquivo.write_text("[]")
    with pytest.raises(ErroSimulador):
        ler_cenario(arquivo)
