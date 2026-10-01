"""Tipos e regras puras dos resultados do M3 (modelos, alertas e antes x depois).

Os resultados sao dado real do CU-BEMS processado offline pelo M3. Todos os instantes aqui tem
fuso (o adaptador converte a hora local ingenua do artefato). Nada aqui e economia real: o antes
x depois valida o METODO com uma reducao sintetica, e os alertas sao candidatos nao corroborados.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TipoAlerta = Literal["zscore", "lightgbm"]
TIPOS_ALERTA: tuple[TipoAlerta, ...] = ("zscore", "lightgbm")

ROTULO_ALERTA = "candidato, nao corroborado"


@dataclass(frozen=True)
class Janela:
    inicio: datetime
    fim: datetime


# ---------------------------------------------------------------- resumo dos modelos


@dataclass(frozen=True)
class DadosSubconjunto:
    fonte: str
    periodo: Janela
    treino: Janela
    reservado: Janela
    equipamentos_no_andar: int
    equipamentos_modelados: int
    equipamentos_sem_carga: tuple[str, ...]
    linhas_minuto: int


@dataclass(frozen=True)
class MaeEquipamento:
    equipamento: str
    horas_teste: int
    mae_baseline_kw: float
    mae_lightgbm_kw: float
    melhora_pct: float


@dataclass(frozen=True)
class MaeModelos:
    horas_teste: int
    baseline_sazonal_kw: float
    lightgbm_kw: float
    melhora_mediana_pct: float
    ressalva_nowcast: str
    por_equipamento: tuple[MaeEquipamento, ...]


@dataclass(frozen=True)
class ParticipacaoFeature:
    feature: str
    pct: float


@dataclass(frozen=True)
class ShapEquipamento:
    equipamento: str
    calendario_pct: float
    historico_pct: float
    feature_dominante: str | None


@dataclass(frozen=True)
class ResumoShap:
    horas_equipamento: int
    calendario_pct: float
    historico_pct: float
    limiar_feature_dominante_pct: float
    por_feature: tuple[ParticipacaoFeature, ...]
    por_equipamento: tuple[ShapEquipamento, ...]


@dataclass(frozen=True)
class DeteccaoPorTipo:
    tipo: str
    detectados: int
    eventos: int


@dataclass(frozen=True)
class DetectorSintetico:
    detector: TipoAlerta
    por_tipo: tuple[DeteccaoPorTipo, ...]
    total_detectados: int
    total_eventos: int
    falso_alarme_horas: int
    horas_base: int


@dataclass(frozen=True)
class BenchmarkSintetico:
    semente: int
    eventos_por_tipo_por_equipamento: int
    limiar_z: float
    detectores: tuple[DetectorSintetico, ...]


@dataclass(frozen=True)
class CriterioBaselineFraca:
    criterio: str
    semanas_completas_treino: int


@dataclass(frozen=True)
class ResumoM3:
    sensor_id: str
    dados: DadosSubconjunto
    mae: MaeModelos
    shap: ResumoShap
    benchmark_sintetico: BenchmarkSintetico
    baseline_fraca: CriterioBaselineFraca


@dataclass(frozen=True)
class AvisoD7:
    """Aviso de feature dominante: uma feature passa do limiar da atribuicao SHAP agregada."""

    disparado: bool
    feature: str | None
    pct: float | None
    limiar_pct: float
    equipamentos_com_dominante: int


def avaliar_aviso_d7(shap: ResumoShap) -> AvisoD7:
    """Derivado dos dados: dispara se a maior feature agregada passa do limiar."""
    limiar = shap.limiar_feature_dominante_pct
    dominantes = sum(1 for e in shap.por_equipamento if e.feature_dominante is not None)
    if not shap.por_feature:
        return AvisoD7(False, None, None, limiar, dominantes)
    topo = max(shap.por_feature, key=lambda f: f.pct)
    return AvisoD7(topo.pct > limiar, topo.feature, topo.pct, limiar, dominantes)


# ---------------------------------------------------------------- alertas


@dataclass(frozen=True)
class ContribuicaoShap:
    feature: str
    shap: float


@dataclass(frozen=True)
class AlertaM3:
    equipamento: str
    timestamp: datetime
    tipo: TipoAlerta
    esperado_kw: float
    observado_kw: float
    z: float
    janela_baseline: Janela
    top_shap: tuple[ContribuicaoShap, ...] | None
    baseline_fraca: bool


@dataclass(frozen=True)
class AlertasM3:
    sensor_id: str
    periodo: Janela
    limiar_z: float
    aviso: str
    alertas: tuple[AlertaM3, ...]


@dataclass(frozen=True)
class FiltroAlertas:
    equipamento: str | None = None
    tipo: TipoAlerta | None = None
    de: datetime | None = None
    ate: datetime | None = None


def filtrar_alertas(alertas: tuple[AlertaM3, ...], f: FiltroAlertas) -> list[AlertaM3]:
    """Filtra (`de` inclusivo, `ate` exclusivo) e ordena por instante, equipamento e tipo."""
    achados = [
        a
        for a in alertas
        if (f.equipamento is None or a.equipamento == f.equipamento)
        and (f.tipo is None or a.tipo == f.tipo)
        and (f.de is None or a.timestamp >= f.de)
        and (f.ate is None or a.timestamp < f.ate)
    ]
    return sorted(achados, key=lambda a: (a.timestamp, a.equipamento, a.tipo))


# ---------------------------------------------------------------- antes x depois


@dataclass(frozen=True)
class EconomiaEquipamento:
    equipamento: str
    kwh_antes: float
    kwh_depois: float
    kwh_contrafactual: float | None
    economia_kwh: float | None
    economia_pct: float | None
    economia_pct_sem_reducao: float | None
    recuperado_pct: float | None
    reducao_sintetica_aplicada: bool
    baseline_fraca: bool


@dataclass(frozen=True)
class ReducaoSintetica:
    equipamento: str
    fracao_pct: float
    a_partir_de: datetime


@dataclass(frozen=True)
class EconomiaM3:
    sensor_id: str
    natureza: str
    aviso: str
    periodo_antes: Janela
    periodo_depois: Janela
    reducao: ReducaoSintetica
    recuperado_pct: float | None
    tolerancia_pp: float
    dentro_da_tolerancia: bool
    equipamentos: tuple[EconomiaEquipamento, ...]


@dataclass(frozen=True)
class ComparacaoEquipamento:
    """Linha do antes x depois: a mesma reducao injetada, e quanto o metodo recuperou."""

    equipamento: str
    injetado_pct: float
    recuperado_pct: float | None
    erro_pp: float | None
    tolerancia_pp: float
    dentro_da_tolerancia: bool
    economia_pct_sem_reducao: float | None
    baseline_fraca: bool


@dataclass(frozen=True)
class Veredito:
    """Veredito geral, derivado dos numeros do artefato (nada fixo)."""

    tolerancia_atendida: bool
    equipamentos: int
    dentro_da_tolerancia: int
    alvo_equipamento: str
    alvo_injetado_pct: float
    alvo_recuperado_pct: float | None
    alvo_dentro_da_tolerancia: bool
    erro_abs_mediano_pp: float | None
    erro_abs_maximo_pp: float | None
    texto: str


def _fmt(v: float | None) -> str:
    return "n/d" if v is None else f"{v:.2f}"


def comparar(e: EconomiaM3) -> list[ComparacaoEquipamento]:
    """Compara a reducao injetada com a recuperada, por equipamento."""
    saida: list[ComparacaoEquipamento] = []
    for x in e.equipamentos:
        rec = x.recuperado_pct
        erro = None if rec is None or math.isnan(rec) else rec - e.reducao.fracao_pct
        saida.append(
            ComparacaoEquipamento(
                equipamento=x.equipamento,
                injetado_pct=e.reducao.fracao_pct,
                recuperado_pct=rec,
                erro_pp=erro,
                tolerancia_pp=e.tolerancia_pp,
                dentro_da_tolerancia=erro is not None and abs(erro) <= e.tolerancia_pp,
                economia_pct_sem_reducao=x.economia_pct_sem_reducao,
                baseline_fraca=x.baseline_fraca,
            )
        )
    return saida


def veredito(e: EconomiaM3) -> Veredito:
    linhas = comparar(e)
    dentro = sum(1 for c in linhas if c.dentro_da_tolerancia)
    erros = [abs(c.erro_pp) for c in linhas if c.erro_pp is not None]
    atendida = e.dentro_da_tolerancia and dentro == len(linhas)
    resultado = "atendida" if atendida else "NAO atendida"
    texto = (
        f"Tolerancia de +-{e.tolerancia_pp:.1f} pp {resultado} em dado real: {dentro} de {len(linhas)} "
        f"equipamentos recuperam a reducao sintetica de {e.reducao.fracao_pct:.1f}% dentro da tolerancia; "
        f"o alvo {e.reducao.equipamento} recuperou {_fmt(e.recuperado_pct)}%. "
        "Valida o metodo, nao e economia real."
    )
    return Veredito(
        tolerancia_atendida=atendida,
        equipamentos=len(linhas),
        dentro_da_tolerancia=dentro,
        alvo_equipamento=e.reducao.equipamento,
        alvo_injetado_pct=e.reducao.fracao_pct,
        alvo_recuperado_pct=e.recuperado_pct,
        alvo_dentro_da_tolerancia=e.dentro_da_tolerancia,
        erro_abs_mediano_pp=statistics.median(erros) if erros else None,
        erro_abs_maximo_pp=max(erros) if erros else None,
        texto=texto,
    )


def equipamentos_com_baseline_fraca(alertas: AlertasM3, economia: EconomiaM3) -> list[str]:
    """Uniao dos equipamentos marcados com baseline fraca no antes x depois ou em algum alerta."""
    fracos = {x.equipamento for x in economia.equipamentos if x.baseline_fraca}
    fracos |= {a.equipamento for a in alertas.alertas if a.baseline_fraca}
    return sorted(fracos)
