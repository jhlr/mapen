"""Semente de demo: cadastra empresas, sensores e equipamentos sobre a `leitura` carregada pelo M1."""

from __future__ import annotations

from mapen_aconselhamento.recomenda import ConfigEquipamentos
from mapen_plataforma.domain.entidades import Empresa, Equipamento, Sensor, Unidade
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.repositorios import (
    EmpresaDuckDB,
    EquipamentoDuckDB,
    SensorDuckDB,
    UnidadeDuckDB,
)

EMPRESA_DEMO = "demo"
EMPRESA_OUTRA = "outra"
SENSOR_CU_BEMS = "cu_bems_2018Floor2"
SENSOR_PANTHER = "Panther_parking_Lorriane"


def semear_demo(banco: BancoDuckDB) -> None:
    """Idempotente: nao recria o que ja existe. `critico` vem de config/equipamentos.yaml (M1)."""
    empresas, unidades = EmpresaDuckDB(banco), UnidadeDuckDB(banco)
    sensores, equipamentos = SensorDuckDB(banco), EquipamentoDuckDB(banco)
    config = ConfigEquipamentos.carregar()
    for empresa_id, nome, sensor_id in (
        (EMPRESA_DEMO, "Empresa Demo (CU-BEMS)", SENSOR_CU_BEMS),
        (EMPRESA_OUTRA, "Outra Empresa (BDG2)", SENSOR_PANTHER),
    ):
        if empresas.obter(empresa_id) is not None:
            continue
        empresas.adicionar(Empresa(empresa_id, nome))
        unidade = Unidade(f"{empresa_id}-u1", empresa_id, "Unidade principal")
        unidades.adicionar(unidade)
        sensores.adicionar(Sensor(sensor_id, empresa_id, unidade.id, sensor_id))
        nomes = [
            str(linha[0])
            for linha in banco.consultar(
                "SELECT DISTINCT equipamento_id FROM leitura WHERE sensor_id = ? ORDER BY 1", [sensor_id]
            )
        ]
        for nome_eq in nomes:
            equipamentos.adicionar(
                Equipamento(f"{sensor_id}:{nome_eq}", empresa_id, sensor_id, nome_eq, config.para(nome_eq).critico)
            )
