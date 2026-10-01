"""Raiz de composicao: liga adaptadores de infraestrutura aos casos de uso."""

from __future__ import annotations

import os
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI

from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_plataforma.application.casos_de_uso import (
    AlterarConfiguracao,
    AlterarRegra,
    AutenticarDispositivo,
    AutenticarEmpresa,
    Cadastro,
    ConsumoAgoraEHoje,
    ConsumoHorario,
    CriarRegraDesligamento,
    EmitirCredenciaisDispositivo,
    ListarConsumoECusto,
    ListarEventos,
    ListarRegras,
    ObterConfiguracao,
    ProvisionarEmpresa,
    RankingEquipamentos,
    RegistrarLeitura,
    SolicitarDesligamento,
)
from mapen_plataforma.application.portas import (
    Atuador,
    CalculadoraCusto,
    DerivadorChave,
    GeradorId,
    Relogio,
    ResultadosM3Repositorio,
)
from mapen_plataforma.application.resultados_m3 import ConsultarEconomiaM3, ConsultarResumoM3, ListarAlertasM3
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.demo import EMPRESA_DEMO, EMPRESA_OUTRA, SegredosDemo, semear_demo
from mapen_plataforma.infrastructure.resultados_m3_json import ResultadosM3Json
from mapen_plataforma.infrastructure.repositorios import (
    ConfiguracaoDuckDB,
    CredenciaisDispositivoDuckDB,
    CredenciaisEmpresaDuckDB,
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
    ChavesDerivadas,
    DerivadorHmac,
    GeradorUuid,
    RelogioSistema,
)
from mapen_plataforma.interface.api.app import Servicos, criar_app

DB_M1: Path = RAIZ / "data" / "mapen_m1.duckdb"
DB_M2: Path = RAIZ / "data" / "mapen_m2.duckdb"
DIR_M3: Path = RAIZ / "data" / "m3"


def montar_provisionamento(
    banco: BancoDuckDB, ids: GeradorId, derivador: DerivadorChave
) -> tuple[ProvisionarEmpresa, EmitirCredenciaisDispositivo]:
    """Casos de uso de provisionamento (CLI e demo); eles devolvem os segredos uma unica vez."""
    return (
        ProvisionarEmpresa(EmpresaDuckDB(banco), CredenciaisEmpresaDuckDB(banco), ids),
        EmitirCredenciaisDispositivo(CredenciaisDispositivoDuckDB(banco), derivador),
    )


def montar_servicos(
    banco: BancoDuckDB,
    relogio: Relogio,
    ids: GeradorId,
    derivador: DerivadorChave,
    atuador: Atuador,
    custo: CalculadoraCusto,
    resultados_m3: ResultadosM3Repositorio,
) -> Servicos:
    empresas, unidades = EmpresaDuckDB(banco), UnidadeDuckDB(banco)
    sensores, equipamentos = SensorDuckDB(banco), EquipamentoDuckDB(banco)
    regras, eventos, leituras = RegraDuckDB(banco), EventoDuckDB(banco), LeituraDuckDB(banco)
    cred_disp, configuracao = CredenciaisDispositivoDuckDB(banco), ConfiguracaoDuckDB(banco)
    emitir = EmitirCredenciaisDispositivo(cred_disp, derivador)
    return Servicos(
        autenticar_empresa=AutenticarEmpresa(CredenciaisEmpresaDuckDB(banco)),
        autenticar_dispositivo=AutenticarDispositivo(cred_disp),
        cadastro=Cadastro(empresas, unidades, sensores, equipamentos, emitir, ids),
        registrar_leitura=RegistrarLeitura(sensores, leituras),
        consumo_agora=ConsumoAgoraEHoje(sensores, leituras),
        consumo_horario=ConsumoHorario(sensores, leituras, custo),
        custo=ListarConsumoECusto(sensores, custo),
        ranking=RankingEquipamentos(sensores, custo),
        criar_regra=CriarRegraDesligamento(equipamentos, regras, relogio, ids),
        alterar_regra=AlterarRegra(regras),
        listar_regras=ListarRegras(regras),
        obter_configuracao=ObterConfiguracao(configuracao),
        alterar_configuracao=AlterarConfiguracao(configuracao, eventos, relogio, ids),
        desligar=SolicitarDesligamento(
            equipamentos, regras, eventos, NonceDuckDB(banco), ChavesDerivadas(cred_disp, derivador),
            configuracao, atuador, relogio, ids,
        ),
        eventos=ListarEventos(eventos),
        resumo_m3=ConsultarResumoM3(resultados_m3),
        alertas_m3=ListarAlertasM3(resultados_m3),
        economia_m3=ConsultarEconomiaM3(resultados_m3),
    )


def segredo_mestre_do_ambiente() -> bytes:
    """`MAPEN_SEGREDO_MESTRE` (>= 32 caracteres) ou um segredo aleatorio so desta execucao.

    Sem a variavel, as chaves de comando dos dispositivos deixam de valer quando o processo
    reinicia (a demo reemite tudo na partida).
    """
    valor = os.environ.get("MAPEN_SEGREDO_MESTRE")
    return valor.encode() if valor else secrets.token_bytes(32)


@dataclass(frozen=True)
class AppDemo:
    app: FastAPI
    segredos: list[SegredosDemo]


def montar_app_demo(
    caminho: Path,
    segredo_mestre: bytes,
    chaves_api: dict[str, str] | None = None,
    dir_m3: Path = DIR_M3,
) -> AppDemo:
    """App de demo sobre uma copia do banco do M1; reemite as chaves de demo a cada chamada.

    Os resultados do M3 (`dir_m3`) so aparecem para a empresa demo.
    """
    if not caminho.exists():
        shutil.copy2(DB_M1, caminho)
    banco = BancoDuckDB(caminho)
    ids, derivador = GeradorUuid(), DerivadorHmac(segredo_mestre)
    provisionar, emitir = montar_provisionamento(banco, ids, derivador)
    segredos = semear_demo(banco, provisionar, emitir, chaves_api)
    servicos = montar_servicos(
        banco, RelogioSistema(), ids, derivador, AtuadorSimulado(), CalculadoraM1(banco),
        ResultadosM3Json(dir_m3, EMPRESA_DEMO),
    )
    return AppDemo(criar_app(servicos), segredos)


def criar_app_padrao() -> FastAPI:
    """App de demo (uvicorn --factory).

    Banco em `MAPEN_DB` (padrao data/mapen_m2.duckdb); resultados do M3 em `MAPEN_M3_DIR` (padrao data/m3). A cada partida as empresas `demo` e `outra`
    ganham chave de API nova (ou a de `MAPEN_CHAVE_API_DEMO` / `MAPEN_CHAVE_API_OUTRA`, minimo 32
    caracteres), e cada sensor de demo ganha token e chave de comando novos. Os segredos
    novos sao impressos uma vez no stdout.
    """
    caminho = Path(os.environ.get("MAPEN_DB", str(DB_M2)))
    fixas = {
        empresa: valor
        for empresa, variavel in ((EMPRESA_DEMO, "MAPEN_CHAVE_API_DEMO"), (EMPRESA_OUTRA, "MAPEN_CHAVE_API_OUTRA"))
        if (valor := os.environ.get(variavel))
    }
    dir_m3 = Path(os.environ.get("MAPEN_M3_DIR", str(DIR_M3)))
    demo = montar_app_demo(caminho, segredo_mestre_do_ambiente(), fixas, dir_m3)
    for s in demo.segredos:
        print(
            f"[demo] empresa={s.empresa_id} chave_api={s.chave_api} sensor={s.sensor_id} "
            f"token_dispositivo={s.dispositivo.token} chave_comando={s.dispositivo.chave_comando}",
            flush=True,
        )
    return demo.app
