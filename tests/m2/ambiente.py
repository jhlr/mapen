from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from mapen_aconselhamento.tarifa import Tarifas
from mapen_plataforma.application.casos_de_uso import EmitirCredenciaisDispositivo, ProvisionarEmpresa
from mapen_plataforma.application.portas import Atuador
from mapen_plataforma.domain.comando import Acao, ConfiguracaoSeguranca, assinar
from mapen_plataforma.domain.entidades import Equipamento, Leitura, Sensor, Unidade
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.custo_m1 import CalculadoraM1
from mapen_plataforma.infrastructure.repositorios import (
    ConfiguracaoDuckDB,
    EquipamentoDuckDB,
    LeituraDuckDB,
    SensorDuckDB,
    UnidadeDuckDB,
)
from mapen_plataforma.infrastructure.servicos import (
    AtuadorSimulado,
    DerivadorHmac,
    GeradorSequencial,
    RelogioFixo,
)
from mapen_plataforma.interface.api.app import Servicos, criar_app
from mapen_plataforma.interface.api.composicao import montar_provisionamento, montar_servicos

AGORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
SEGREDO_MESTRE = b"segredo-mestre-de-teste-0123456789"
FUSO = "-03:00"


def bearer(chave: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {chave}"}


@dataclass
class Ambiente:
    client: TestClient
    banco: BancoDuckDB
    relogio: RelogioFixo
    atuador: Atuador
    servicos: Servicos
    provisionar: ProvisionarEmpresa
    emitir: EmitirCredenciaisDispositivo
    chaves_api: dict[str, str]
    tokens: dict[str, str]
    chaves_comando: dict[str, bytes]
    ids: GeradorSequencial = field(default_factory=GeradorSequencial)

    @property
    def ha(self) -> dict[str, str]:
        return bearer(self.chaves_api["emp-a"])

    @property
    def hb(self) -> dict[str, str]:
        return bearer(self.chaves_api["emp-b"])

    def habilitar(self, empresa_id: str = "emp-a", valor: bool = True) -> None:
        ConfiguracaoDuckDB(self.banco).definir(empresa_id, ConfiguracaoSeguranca(valor))

    def comando(
        self,
        device_id: str = "sa",
        acao: Acao = Acao.DESLIGAR,
        nonce: str = "n1",
        validade_s: float = 30,
        emitido_s: float = 0,
        chave: bytes | None = None,
        empresa_id: str = "emp-a",
        equipamento_id: str = "eq-ac",
    ) -> dict[str, str]:
        """Corpo do comando como o dispositivo o assina (offsets em segundos a partir de AGORA)."""
        emitido, validade = AGORA + timedelta(seconds=emitido_s), AGORA + timedelta(seconds=validade_s)
        usada = chave if chave is not None else self.chaves_comando[device_id]
        return {
            "device_id": device_id,
            "acao": acao.value,
            "nonce": nonce,
            "emitido_em": emitido.isoformat(),
            "validade": validade.isoformat(),
            "assinatura": assinar(usada, device_id, empresa_id, equipamento_id, acao, nonce, emitido, validade),
        }


def _leituras_sinteticas(sensor_id: str, equipamento: str, watts: float) -> list[Leitura]:
    """Segunda 2026-10-05 17:00-18:59 (hora local), 1 min: 60 min intermediario + 60 min ponta."""
    from mapen_plataforma.domain.tempo import de_local_ingenuo

    ts = pd.date_range("2026-10-05 17:00", "2026-10-05 19:00", freq="1min", inclusive="left")
    return [
        Leitura(sensor_id, equipamento, de_local_ingenuo(t.to_pydatetime()), watts, None, watts / 1000 / 60)
        for t in ts
    ]


def montar(habilitado: bool = True, caminho: str | Path = ":memory:", atuador: Atuador | None = None) -> Ambiente:
    banco = BancoDuckDB(caminho)
    ids, derivador = GeradorSequencial(), DerivadorHmac(SEGREDO_MESTRE)
    provisionar, emitir = montar_provisionamento(banco, ids, derivador)
    unidades, sensores, equipamentos = UnidadeDuckDB(banco), SensorDuckDB(banco), EquipamentoDuckDB(banco)
    chaves_api: dict[str, str] = {}
    tokens: dict[str, str] = {}
    chaves_comando: dict[str, bytes] = {}
    for emp, sensor in (("emp-a", "sa"), ("emp-b", "sb")):
        _, chaves_api[emp] = provisionar.executar(emp, "ana", emp)
        unidades.adicionar(Unidade(f"u-{emp}", emp, "u"))
        sensores.adicionar(Sensor(sensor, emp, f"u-{emp}", sensor))
        novas = emitir.executar(emp, sensor)
        tokens[sensor], chaves_comando[sensor] = novas.token, bytes.fromhex(novas.chave_comando)
    equipamentos.adicionar(Equipamento("eq-ac", "emp-a", "sa", "AC1", False))
    equipamentos.adicionar(Equipamento("eq-crit", "emp-a", "sa", "UTI", True))
    equipamentos.adicionar(Equipamento("eq-b", "emp-b", "sb", "AC1", False))
    leituras = LeituraDuckDB(banco)
    leituras.adicionar(_leituras_sinteticas("sa", "AC1", 2000.0))
    leituras.adicionar(_leituras_sinteticas("sb", "AC1", 1000.0))
    relogio = RelogioFixo(AGORA)
    usado = atuador or AtuadorSimulado()
    servicos = montar_servicos(
        banco, relogio, GeradorSequencial("srv"), derivador, usado, CalculadoraM1(banco, Tarifas.carregar())
    )
    amb = Ambiente(
        TestClient(criar_app(servicos)), banco, relogio, usado, servicos, provisionar, emitir,
        chaves_api, tokens, chaves_comando,
    )
    if habilitado:
        amb.habilitar("emp-a")
        amb.habilitar("emp-b")
    return amb
