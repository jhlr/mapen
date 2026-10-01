"""API real da plataforma em processo (FastAPI + TestClient) com um dispositivo e tres equipamentos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from mapen_aconselhamento.infrastructure.tarifa_csv import carregar_tarifas
from mapen_plataforma.application.casos_de_uso import EmitirCredenciaisDispositivo, ProvisionarEmpresa
from mapen_plataforma.domain.comando import ConfiguracaoSeguranca
from mapen_plataforma.domain.entidades import Equipamento, Sensor, Unidade
from mapen_plataforma.domain.tempo import FUSO_LOCAL, para_local_ingenuo
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.repositorios import (
    ConfiguracaoDuckDB,
    CredenciaisDispositivoDuckDB,
    EquipamentoDuckDB,
    SensorDuckDB,
    UnidadeDuckDB,
)
from mapen_plataforma.infrastructure.resultados_m3_json import ResultadosM3Json
from mapen_plataforma.infrastructure.servicos import AtuadorSimulado, DerivadorHmac, GeradorSequencial, RelogioFixo
from mapen_plataforma.interface.api.app import criar_app
from mapen_plataforma.interface.api.composicao import montar_provisionamento, montar_servicos
from mapen_simulador.application.portas import EnvioLeituras
from mapen_simulador.domain.amostras import LoteLeituras
from mapen_simulador.domain.carga import SerieCarga

SEGREDO_MESTRE = b"segredo-mestre-do-simulador-0123456789"
EMPRESA = "emp-sim"
DEVICE = "disp-1"
EQ_AC = "eq-ac"
EQ_AC2 = "eq-ac2"
EQ_CRITICO = "eq-crit"
NOME_AC = "AC1"
INICIO = datetime(2026, 10, 5, 10, 0, tzinfo=FUSO_LOCAL)
"""Inicio das series de teste (hora local de Recife)."""


def minuto(n: float) -> datetime:
    return INICIO + timedelta(minutes=n)


@dataclass
class Ambiente:
    client: TestClient
    banco: BancoDuckDB
    relogio: RelogioFixo
    chave_api: str
    token: str
    chave_comando: bytes
    sal: str
    ids: GeradorSequencial = field(default_factory=GeradorSequencial)

    def habilitar(self, valor: bool = True) -> None:
        ConfiguracaoDuckDB(self.banco).definir(EMPRESA, ConfiguracaoSeguranca(valor))

    def timestamps_gravados(self, equipamento: str = NOME_AC) -> list[datetime]:
        linhas = self.banco.consultar(
            "SELECT ts FROM leitura WHERE sensor_id = ? AND equipamento_id = ? ORDER BY ts", [DEVICE, equipamento]
        )
        return [t for (t,) in linhas if isinstance(t, datetime)]

    def total_gravado(self) -> int:
        n = self.banco.consultar("SELECT count(*) FROM leitura WHERE sensor_id = ?", [DEVICE])[0][0]
        assert isinstance(n, int)
        return n

    def distintos_gravados(self) -> int:
        n = self.banco.consultar(
            "SELECT count(*) FROM (SELECT DISTINCT equipamento_id, ts FROM leitura WHERE sensor_id = ?)", [DEVICE]
        )[0][0]
        assert isinstance(n, int)
        return n


def montar(habilitado: bool = True, caminho: str | Path = ":memory:") -> Ambiente:
    banco = BancoDuckDB(caminho)
    ids, derivador = GeradorSequencial(), DerivadorHmac(SEGREDO_MESTRE)
    provisionar, emitir = montar_provisionamento(banco, ids, derivador)
    _, chave_api = provisionar.executar(EMPRESA, "ana", EMPRESA)
    UnidadeDuckDB(banco).adicionar(Unidade("u1", EMPRESA, "u"))
    SensorDuckDB(banco).adicionar(Sensor(DEVICE, EMPRESA, "u1", DEVICE))
    novas = emitir.executar(EMPRESA, DEVICE)
    equipamentos = EquipamentoDuckDB(banco)
    equipamentos.adicionar(Equipamento(EQ_AC, EMPRESA, DEVICE, NOME_AC, False))
    equipamentos.adicionar(Equipamento(EQ_AC2, EMPRESA, DEVICE, "AC2", False))
    equipamentos.adicionar(Equipamento(EQ_CRITICO, EMPRESA, DEVICE, "UTI", True))
    relogio = RelogioFixo(INICIO)
    servicos = montar_servicos(
        banco, relogio, GeradorSequencial("srv"), derivador, AtuadorSimulado(),
        CalculadoraM1(banco, carregar_tarifas()), ResultadosM3Json(Path("/nonexistent-m3-dir"), EMPRESA),
    )
    credencial = CredenciaisDispositivoDuckDB(banco).obter(DEVICE)
    assert credencial is not None
    amb = Ambiente(
        TestClient(criar_app(servicos)), banco, relogio, chave_api, novas.token,
        bytes.fromhex(novas.chave_comando), credencial.sal,
    )
    if habilitado:
        amb.habilitar()
    return amb


class FonteSintetica:
    """Fonte de serie de teste: potencia constante por minuto (porta `FonteSerie`)."""

    def __init__(self, potencia_w: float = 1200.0) -> None:
        self._potencia = potencia_w

    def carregar(self, equipamento: str, inicio: datetime, duracao: timedelta) -> SerieCarga:
        n = int(duracao / timedelta(minutes=1))
        return SerieCarga(equipamento, inicio, timedelta(minutes=1), tuple(self._potencia for _ in range(n)))


class EnvioGravador:
    """Envolve um envio real e guarda cada lote tentado (para inspecionar o que foi mandado quando)."""

    def __init__(self, interno: EnvioLeituras) -> None:
        self._interno = interno
        self.lotes: list[LoteLeituras] = []

    def enviar(self, lote: LoteLeituras) -> bool:
        self.lotes.append(lote)
        return self._interno.enviar(lote)


class EnvioDuplicado:
    """Reenvia cada lote uma segunda vez, como um dispositivo que nao viu o ack."""

    def __init__(self, interno: EnvioLeituras) -> None:
        self._interno = interno
        self.reenvios = 0

    def enviar(self, lote: LoteLeituras) -> bool:
        ok = self._interno.enviar(lote)
        self._interno.enviar(lote)
        self.reenvios += 1
        return ok


class EnvioPerdeAck:
    """O servidor grava o lote mas o ack se perde na primeira tentativa de cada lote."""

    def __init__(self, interno: EnvioLeituras) -> None:
        self._interno = interno
        self._vistos: set[str] = set()
        self.acks_perdidos = 0

    def enviar(self, lote: LoteLeituras) -> bool:
        ok = self._interno.enviar(lote)
        if lote.id not in self._vistos:
            self._vistos.add(lote.id)
            self.acks_perdidos += 1
            return False
        return ok


def esperado_local(instantes: list[datetime]) -> list[datetime]:
    """Instantes com fuso -> o que a tabela `leitura` guarda (hora local ingenua)."""
    return [para_local_ingenuo(t) for t in instantes]
