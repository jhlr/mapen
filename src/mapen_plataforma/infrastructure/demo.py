"""Semente de demo: empresas, sensores e equipamentos sobre a `leitura` carregada pelo M1.

Cada partida emite chaves novas (empresa e dispositivo); os segredos so existem no retorno.
"""

from __future__ import annotations

from dataclasses import dataclass

from mapen_aconselhamento.domain.equipamentos import ConfigEquipamentos
from mapen_aconselhamento.infrastructure.equipamentos_yaml import carregar_config_equipamentos
from mapen_plataforma.application.casos_de_uso import EmitirCredenciaisDispositivo, ProvisionarEmpresa
from mapen_plataforma.domain.credenciais import CredenciaisNovas
from mapen_plataforma.domain.entidades import Equipamento, Sensor, Unidade
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.repositorios import EquipamentoDuckDB, SensorDuckDB, UnidadeDuckDB

EMPRESA_DEMO = "demo"
EMPRESA_OUTRA = "outra"
SENSOR_CU_BEMS = "cu_bems_2018Floor2"
SENSOR_PANTHER = "Panther_parking_Lorriane"

_DEMOS: tuple[tuple[str, str, str], ...] = (
    (EMPRESA_DEMO, "Empresa Demo (CU-BEMS)", SENSOR_CU_BEMS),
    (EMPRESA_OUTRA, "Outra Empresa (BDG2)", SENSOR_PANTHER),
)


@dataclass(frozen=True)
class SegredosDemo:
    """Segredos em texto puro de uma empresa de demo, para imprimir uma vez."""

    empresa_id: str
    chave_api: str
    sensor_id: str
    dispositivo: CredenciaisNovas


def critico_inicial(config: ConfigEquipamentos, equipamento: str) -> bool:
    """Falha fechada: equipamento que nao casa com o YAML e critico ate ser classificado."""
    regra = config.encontrar(equipamento)
    return True if regra is None else regra.critico


def semear_demo(
    banco: BancoDuckDB,
    provisionar_empresa: ProvisionarEmpresa,
    emitir_dispositivo: EmitirCredenciaisDispositivo,
    chaves_api: dict[str, str] | None = None,
) -> list[SegredosDemo]:
    """Cria o que falta (idempotente) e rotaciona as chaves de demo. `chaves_api` fixa a chave por empresa."""
    unidades, sensores, equipamentos = UnidadeDuckDB(banco), SensorDuckDB(banco), EquipamentoDuckDB(banco)
    config = carregar_config_equipamentos()
    segredos: list[SegredosDemo] = []
    for empresa_id, nome, sensor_id in _DEMOS:
        novo = not banco.consultar("SELECT 1 FROM empresa WHERE id = ?", [empresa_id])
        _, chave = provisionar_empresa.executar(
            nome, "admin", empresa_id, (chaves_api or {}).get(empresa_id)
        )
        if novo:
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
                    Equipamento(
                        f"{sensor_id}:{nome_eq}", empresa_id, sensor_id, nome_eq, critico_inicial(config, nome_eq)
                    )
                )
        segredos.append(
            SegredosDemo(empresa_id, chave, sensor_id, emitir_dispositivo.executar(empresa_id, sensor_id))
        )
    return segredos
