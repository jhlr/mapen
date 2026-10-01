from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd
from fastapi.testclient import TestClient

from mapen_aconselhamento.tarifa import Tarifas
from mapen_plataforma.domain.comando import Acao, ConfiguracaoSeguranca, assinar
from mapen_plataforma.domain.entidades import Empresa, Equipamento, Leitura, Sensor, Unidade
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.repositorios import (
    EmpresaDuckDB,
    EquipamentoDuckDB,
    LeituraDuckDB,
    SensorDuckDB,
    UnidadeDuckDB,
)
from mapen_plataforma.infrastructure.servicos import (
    AtuadorSimulado,
    ChavesEmMemoria,
    GeradorSequencial,
    RelogioFixo,
)
from mapen_plataforma.interface.api.app import criar_app
from mapen_plataforma.interface.api.composicao import montar_servicos

AGORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
CHAVE_A = b"chave-sensor-a"
CHAVE_B = b"chave-sensor-b"
HA = {"X-Empresa-Id": "emp-a"}
HB = {"X-Empresa-Id": "emp-b"}


@dataclass
class Ambiente:
    client: TestClient
    banco: BancoDuckDB
    relogio: RelogioFixo
    atuador: AtuadorSimulado
    chaves: ChavesEmMemoria
    habilitar_desligamento: bool

    def comando(
        self,
        device_id: str = "sa",
        acao: Acao = Acao.DESLIGAR,
        nonce: str = "n1",
        validade_s: float = 60,
        chave: bytes = CHAVE_A,
    ) -> dict[str, str]:
        validade = AGORA + timedelta(seconds=validade_s)
        return {
            "device_id": device_id,
            "acao": acao.value,
            "nonce": nonce,
            "validade": validade.isoformat(),
            "assinatura": assinar(chave, device_id, acao, nonce, validade),
        }


def _leituras_sinteticas(sensor_id: str, equipamento: str, watts: float) -> list[Leitura]:
    """Segunda 2026-10-05 17:00-18:59, 1 min: 60 min intermediario + 60 min ponta."""
    ts = pd.date_range("2026-10-05 17:00", "2026-10-05 19:00", freq="1min", inclusive="left")
    return [Leitura(sensor_id, equipamento, t.to_pydatetime(), watts, None, watts / 1000 / 60) for t in ts]


def montar(habilitado: bool) -> Ambiente:
    banco = BancoDuckDB()
    empresas, unidades = EmpresaDuckDB(banco), UnidadeDuckDB(banco)
    sensores, equipamentos = SensorDuckDB(banco), EquipamentoDuckDB(banco)
    for emp, sensor in (("emp-a", "sa"), ("emp-b", "sb")):
        empresas.adicionar(Empresa(emp, emp))
        unidades.adicionar(Unidade(f"u-{emp}", emp, "u"))
        sensores.adicionar(Sensor(sensor, emp, f"u-{emp}", sensor))
    equipamentos.adicionar(Equipamento("eq-ac", "emp-a", "sa", "AC1", False))
    equipamentos.adicionar(Equipamento("eq-crit", "emp-a", "sa", "UTI", True))
    equipamentos.adicionar(Equipamento("eq-b", "emp-b", "sb", "AC1", False))
    leituras = LeituraDuckDB(banco)
    leituras.adicionar(_leituras_sinteticas("sa", "AC1", 2000.0))
    leituras.adicionar(_leituras_sinteticas("sb", "AC1", 1000.0))
    relogio = RelogioFixo(AGORA)
    atuador = AtuadorSimulado()
    chaves = ChavesEmMemoria({"sa": CHAVE_A, "sb": CHAVE_B})
    servicos = montar_servicos(
        banco, relogio, GeradorSequencial(), chaves, atuador,
        CalculadoraM1(banco, Tarifas.carregar()), ConfiguracaoSeguranca(habilitado),
    )
    return Ambiente(TestClient(criar_app(servicos)), banco, relogio, atuador, chaves, habilitado)
