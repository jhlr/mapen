"""Raiz de composicao: liga adaptadores de infraestrutura aos casos de uso."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import FastAPI

from mapen_aconselhamento.tarifa import RAIZ
from mapen_plataforma.application.portas import Atuador, CalculadoraCusto, GeradorId, Relogio
from mapen_plataforma.application.casos_de_uso import (
    AlterarRegra,
    Cadastro,
    ConsumoAgoraEHoje,
    CriarRegraDesligamento,
    ListarConsumoECusto,
    ListarEventos,
    ListarRegras,
    RankingEquipamentos,
    RegistrarLeitura,
    SolicitarDesligamento,
)
from mapen_plataforma.domain.comando import ConfiguracaoSeguranca
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.demo import SENSOR_CU_BEMS, SENSOR_PANTHER, semear_demo
from mapen_plataforma.infrastructure.repositorios import (
    EmpresaDuckDB,
    EquipamentoDuckDB,
    EventoDuckDB,
    LeituraDuckDB,
    NonceDuckDB,
    RegraDuckDB,
    SensorDuckDB,
    UnidadeDuckDB,
)
from mapen_plataforma.infrastructure.servicos import (
    AtuadorSimulado,
    ChavesEmMemoria,
    GeradorUuid,
    RelogioSistema,
)
from mapen_plataforma.interface.api.app import Servicos, criar_app

DB_M1: Path = RAIZ / "data" / "mapen_m1.duckdb"
DB_M2: Path = RAIZ / "data" / "mapen_m2.duckdb"


def montar_servicos(
    banco: BancoDuckDB,
    relogio: Relogio,
    ids: GeradorId,
    chaves: ChavesEmMemoria,
    atuador: Atuador,
    custo: CalculadoraCusto,
    config: ConfiguracaoSeguranca,
) -> Servicos:
    empresas, unidades = EmpresaDuckDB(banco), UnidadeDuckDB(banco)
    sensores, equipamentos = SensorDuckDB(banco), EquipamentoDuckDB(banco)
    regras, eventos, leituras = RegraDuckDB(banco), EventoDuckDB(banco), LeituraDuckDB(banco)
    return Servicos(
        empresas=empresas,
        cadastro=Cadastro(empresas, unidades, sensores, equipamentos, ids),
        registrar_leitura=RegistrarLeitura(sensores, leituras),
        consumo_agora=ConsumoAgoraEHoje(sensores, leituras),
        custo=ListarConsumoECusto(sensores, custo),
        ranking=RankingEquipamentos(sensores, custo),
        criar_regra=CriarRegraDesligamento(equipamentos, regras, relogio, ids),
        alterar_regra=AlterarRegra(regras),
        listar_regras=ListarRegras(regras),
        desligar=SolicitarDesligamento(
            equipamentos, regras, eventos, NonceDuckDB(banco), chaves, atuador, relogio, ids, config
        ),
        eventos=ListarEventos(eventos),
    )


def criar_app_padrao() -> FastAPI:
    """App de demo (uvicorn --factory).

    Banco em `MAPEN_DB` (padrao data/mapen_m2.duckdb), criado como copia do banco do M1 na
    primeira execucao. `MAPEN_DESLIGAMENTO_REMOTO=1` liga o desligamento (padrao: desligado).
    `MAPEN_CHAVE_DEMO` define a chave HMAC dos sensores de demo; sem ela todo comando e rejeitado.
    """
    caminho = Path(os.environ.get("MAPEN_DB", str(DB_M2)))
    if not caminho.exists():
        shutil.copy2(DB_M1, caminho)
    banco = BancoDuckDB(caminho)
    semear_demo(banco)
    chaves = ChavesEmMemoria()
    chave_demo = os.environ.get("MAPEN_CHAVE_DEMO")
    if chave_demo:
        for sensor in (SENSOR_CU_BEMS, SENSOR_PANTHER):
            chaves.definir(sensor, chave_demo.encode())
    config = ConfiguracaoSeguranca(os.environ.get("MAPEN_DESLIGAMENTO_REMOTO") == "1")
    servicos = montar_servicos(
        banco, RelogioSistema(), GeradorUuid(), chaves, AtuadorSimulado(), CalculadoraM1(banco), config
    )
    return criar_app(servicos)
