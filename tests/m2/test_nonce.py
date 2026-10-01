"""Nonce: persistencia entre reinicios, uso concorrente, poda e registro atomico."""

from __future__ import annotations

import threading
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ambiente import AGORA, SEGREDO_MESTRE, Ambiente, montar
from mapen_aconselhamento.tarifa import Tarifas
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.repositorios import NonceDuckDB
from mapen_plataforma.infrastructure.servicos import AtuadorSimulado, DerivadorHmac, GeradorSequencial
from mapen_plataforma.interface.api.app import criar_app
from mapen_plataforma.interface.api.composicao import montar_servicos


def _pedir(amb: Ambiente, **cmd: Any) -> int:
    corpo = {"equipamento_id": "eq-ac", "comando": amb.comando(**cmd)}
    return amb.client.post("/desligamentos", json=corpo, headers=amb.ha).status_code


def test_registrar_e_atomico_e_por_dispositivo() -> None:
    nonces = NonceDuckDB(BancoDuckDB())
    expira = AGORA + timedelta(seconds=65)
    assert nonces.registrar("d1", "n", expira) is True
    assert nonces.registrar("d1", "n", expira) is False
    assert nonces.registrar("d2", "n", expira) is True


def test_nonce_sobrevive_ao_reinicio_com_banco_em_arquivo(tmp_path: Path) -> None:
    caminho = tmp_path / "m2.duckdb"
    amb = montar(caminho=caminho)
    assert _pedir(amb, nonce="persistente") == 200
    amb.banco.conexao.close()  # "reinicio": nova conexao, novo app, mesma base
    banco = BancoDuckDB(caminho)
    servicos = montar_servicos(
        banco, amb.relogio, GeradorSequencial("novo"), DerivadorHmac(SEGREDO_MESTRE), AtuadorSimulado(),
        CalculadoraM1(banco, Tarifas.carregar()),
    )
    novo = TestClient(criar_app(servicos))
    corpo = {"equipamento_id": "eq-ac", "comando": amb.comando(nonce="persistente")}
    resposta = novo.post("/desligamentos", json=corpo, headers=amb.ha)
    assert resposta.status_code == 403 and resposta.json()["motivo"] == "nonce_repetido"
    banco.conexao.close()


def test_uso_concorrente_do_mesmo_nonce_so_um_vence_no_repositorio() -> None:
    nonces = NonceDuckDB(BancoDuckDB())
    resultados: list[bool] = []
    largada = threading.Barrier(16)

    def usar() -> None:
        largada.wait()
        resultados.append(nonces.registrar("d1", "corrida", AGORA + timedelta(seconds=65)))

    threads = [threading.Thread(target=usar) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert resultados.count(True) == 1 and resultados.count(False) == 15


def test_uso_concorrente_do_mesmo_comando_via_api_executa_uma_vez(amb: Ambiente) -> None:
    codigos: list[int] = []
    largada = threading.Barrier(8)

    def enviar() -> None:
        largada.wait()
        codigos.append(_pedir(amb, nonce="par"))

    threads = [threading.Thread(target=enviar) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codigos) == [200] + [403] * 7
    executados = [e for e in amb.client.get("/eventos", headers=amb.ha).json() if e["tipo"] == "desligamento_executado"]
    assert len(executados) == 1


def test_poda_remove_so_nonce_com_janela_encerrada() -> None:
    nonces = NonceDuckDB(BancoDuckDB())
    nonces.registrar("d", "velho", AGORA - timedelta(seconds=1))
    nonces.registrar("d", "vivo", AGORA + timedelta(seconds=30))
    assert nonces.podar(AGORA) == 1
    assert nonces.registrar("d", "vivo", AGORA + timedelta(seconds=30)) is False  # ainda lembrado
    assert nonces.registrar("d", "velho", AGORA + timedelta(seconds=30)) is True  # esquecido


def test_a_requisicao_poda_nonces_vencidos(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="a1") == 200
    assert amb.banco.consultar("SELECT count(*) FROM nonce")[0][0] == 1
    amb.relogio.avancar(120)
    assert _pedir(amb, nonce="a2", emitido_s=120, validade_s=150) == 200
    restantes = {str(r[0]) for r in amb.banco.consultar("SELECT nonce FROM nonce")}
    assert restantes == {"a2"}


def test_replay_depois_da_poda_continua_rejeitado_pela_janela(amb: Ambiente) -> None:
    assert _pedir(amb, nonce="r1") == 200
    amb.relogio.avancar(120)
    assert _pedir(amb, nonce="r1") == 403  # validade vencida, mesmo sem o nonce no banco
