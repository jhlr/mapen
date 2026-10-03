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

# Nomes dos dois metodos de antes x depois, como o M3 os grava em `economia.json`.
METODO_BASELINE = "baseline_normalizado"
METODO_CONTROLE = "diferenca_em_diferencas_grupo_controle"
ROTULOS_METODO = {
    METODO_BASELINE: "Baseline normalizado (esperado do treino, nivel ajustado pelo antes)",
    METODO_CONTROLE: "Diferenca em diferencas com grupo-controle (equipamentos sem intervencao)",
}


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
    recuperado_pct_controle: float | None = None
    economia_pct_controle_sem_reducao: float | None = None
    controles_usados: tuple[str, ...] | None = None  # `None` = artefato sem o metodo de controle


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
    recuperado_pct_controle: float | None = None
    dentro_da_tolerancia_controle: bool | None = None  # `None` = artefato sem o metodo de controle


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
    controles: tuple[str, ...] = ()  # so no metodo de controle


@dataclass(frozen=True)
class Veredito:
    """Veredito geral de um metodo, derivado dos numeros do artefato (nada fixo)."""

    metodo: str
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


@dataclass(frozen=True)
class MetodoAvaliado:
    """Um metodo de antes x depois: linha por equipamento e veredito, ambos derivados do artefato."""

    metodo: str
    rotulo: str
    comparacoes: tuple[ComparacaoEquipamento, ...]
    veredito: Veredito


def _recuperado(x: EconomiaEquipamento, metodo: str) -> float | None:
    return x.recuperado_pct_controle if metodo == METODO_CONTROLE else x.recuperado_pct


def _sem_reducao(x: EconomiaEquipamento, metodo: str) -> float | None:
    return x.economia_pct_controle_sem_reducao if metodo == METODO_CONTROLE else x.economia_pct_sem_reducao


def _recuperado_alvo(e: EconomiaM3, metodo: str) -> tuple[float | None, bool]:
    if metodo == METODO_CONTROLE:
        return e.recuperado_pct_controle, bool(e.dentro_da_tolerancia_controle)
    return e.recuperado_pct, e.dentro_da_tolerancia


def comparar(e: EconomiaM3, metodo: str = METODO_BASELINE) -> list[ComparacaoEquipamento]:
    """Compara a reducao injetada com a recuperada por `metodo`, por equipamento."""
    saida: list[ComparacaoEquipamento] = []
    for x in e.equipamentos:
        rec = _recuperado(x, metodo)
        erro = None if rec is None or math.isnan(rec) else rec - e.reducao.fracao_pct
        saida.append(
            ComparacaoEquipamento(
                equipamento=x.equipamento,
                injetado_pct=e.reducao.fracao_pct,
                recuperado_pct=rec,
                erro_pp=erro,
                tolerancia_pp=e.tolerancia_pp,
                dentro_da_tolerancia=erro is not None and abs(erro) <= e.tolerancia_pp,
                economia_pct_sem_reducao=_sem_reducao(x, metodo),
                baseline_fraca=x.baseline_fraca,
                controles=(x.controles_usados or ()) if metodo == METODO_CONTROLE else (),
            )
        )
    return saida


def veredito(e: EconomiaM3, metodo: str = METODO_BASELINE) -> Veredito:
    linhas = comparar(e, metodo)
    dentro = sum(1 for c in linhas if c.dentro_da_tolerancia)
    erros = [abs(c.erro_pp) for c in linhas if c.erro_pp is not None]
    alvo_recuperado, alvo_dentro = _recuperado_alvo(e, metodo)
    atendida = alvo_dentro and dentro == len(linhas)
    resultado = "atendida" if atendida else "NAO atendida"
    texto = (
        f"Tolerancia de +-{e.tolerancia_pp:.1f} pp {resultado} em dado real: {dentro} de {len(linhas)} "
        f"equipamentos recuperam a reducao sintetica de {e.reducao.fracao_pct:.1f}% dentro da tolerancia; "
        f"o alvo {e.reducao.equipamento} recuperou {_fmt(alvo_recuperado)}%. "
        "Valida o metodo, nao e economia real."
    )
    return Veredito(
        metodo=metodo,
        tolerancia_atendida=atendida,
        equipamentos=len(linhas),
        dentro_da_tolerancia=dentro,
        alvo_equipamento=e.reducao.equipamento,
        alvo_injetado_pct=e.reducao.fracao_pct,
        alvo_recuperado_pct=alvo_recuperado,
        alvo_dentro_da_tolerancia=alvo_dentro,
        erro_abs_mediano_pp=statistics.median(erros) if erros else None,
        erro_abs_maximo_pp=max(erros) if erros else None,
        texto=texto,
    )


def avaliar_metodos(e: EconomiaM3) -> tuple[MetodoAvaliado, ...]:
    """Os metodos que o artefato traz: baseline sempre; grupo-controle so se o M3 o gravou."""
    metodos = [METODO_BASELINE]
    if e.dentro_da_tolerancia_controle is not None:
        metodos.append(METODO_CONTROLE)
    return tuple(MetodoAvaliado(m, ROTULOS_METODO[m], tuple(comparar(e, m)), veredito(e, m)) for m in metodos)


# ---------------------------------------------------------------- estudo de previsao


@dataclass(frozen=True)
class MaseEquipamento:
    """MASE de cada previsor em um equipamento (ausente quando o previsor nao previu nenhuma hora)."""

    equipamento: str
    por_modelo: dict[str, float | None]


@dataclass(frozen=True)
class ModeloPrevisao:
    modelo: str
    mae_agregado_kw: float | None
    mediana_mase_reservado: float | None
    mediana_mase_desenvolvimento: float | None
    vitorias_vs_naive168: int | None
    vitorias_melhor_de_todos: int


@dataclass(frozen=True)
class DecisaoPrevisao:
    """A regra de adocao foi pre-registrada e aplicada pelo M3; aqui so o resultado, sem recalcular."""

    regra_aplicada: str
    adotado: str
    passaram_regra_de_ganho: tuple[str, ...]
    melhor_mediana: str
    motivo: str


@dataclass(frozen=True)
class ShapPrevisao:
    participacao_por_grupo: dict[str, float | None]
    participacao_por_feature: dict[str, float | None]
    d7_feature_dominante: str | None
    equipamentos_com_flag: tuple[str, ...]
    horas: int


@dataclass(frozen=True)
class BenchmarkPrevisao:
    previsor: str
    semente: int
    eventos_por_tipo_por_equipamento: int
    limiar_z: float
    injetados: dict[str, int]
    detectados: dict[str, int]
    alertas_fora_da_zona: int
    horas_fora_da_zona: int


@dataclass(frozen=True)
class EstudoPrevisao:
    sensor_id: str
    aviso: str
    horizonte_h: int
    defasagem_minima_h: int
    treino: Janela
    reservado: Janela
    dobras_walk_forward: int
    referencia_mase: str
    equipamentos: tuple[str, ...]
    sem_carga: tuple[str, ...]
    modelos: tuple[ModeloPrevisao, ...]
    mase_por_equipamento: tuple[MaseEquipamento, ...]
    decisao: DecisaoPrevisao
    avisos: tuple[str, ...]
    shap: ShapPrevisao | None
    benchmark: BenchmarkPrevisao | None


def equipamentos_com_baseline_fraca(alertas: AlertasM3, economia: EconomiaM3) -> list[str]:
    """Uniao dos equipamentos marcados com baseline fraca no antes x depois ou em algum alerta."""
    fracos = {x.equipamento for x in economia.equipamentos if x.baseline_fraca}
    fracos |= {a.equipamento for a in alertas.alertas if a.baseline_fraca}
    return sorted(fracos)
