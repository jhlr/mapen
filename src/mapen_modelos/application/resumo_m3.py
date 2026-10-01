"""Resumo do M3 como valor de aplicacao: o que o dashboard mostra de MAE, SHAP, benchmark e baseline.

Montado pelo `ExecutarM3` a partir do `ResultadoM3`, sem I/O. Os numeros sao os do pipeline
(nao arredondados); quem grava o JSON decide a apresentacao.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from mapen_modelos.application.detectar_anomalias import TIPO_LIGHTGBM, TIPO_ZSCORE
from mapen_modelos.application.treinar_e_avaliar import ResultadoTreino
from mapen_modelos.domain.baseline import COBERTURA_SEMANA_COMPLETA, SEMANAS_MINIMAS
from mapen_modelos.domain.explica import LIMIAR_FEATURE_DOMINANTE
from mapen_modelos.domain.injecao import TIPOS

if TYPE_CHECKING:
    from mapen_modelos.application.executar_m3 import ResultadoM3

RESSALVA_NOWCAST = (
    "O LightGBM usa lag 1 h (nowcast de 1 passo); o baseline sazonal nao usa nada recente. "
    "O ganho e esperado e nao prova que o modelo entende mais."
)


@dataclass(frozen=True)
class FonteDados:
    """O que so a camada de carga sabe: descricao da fonte e quantas linhas de minuto foram lidas."""

    descricao: str
    linhas_minuto: int


@dataclass(frozen=True)
class JanelaResumo:
    inicio: pd.Timestamp
    fim: pd.Timestamp


@dataclass(frozen=True)
class DadosResumo:
    fonte: str
    periodo: JanelaResumo
    treino: JanelaResumo
    reservado: JanelaResumo
    equipamentos_no_andar: int
    equipamentos_modelados: int
    equipamentos_sem_carga: tuple[str, ...]
    linhas_minuto: int


@dataclass(frozen=True)
class MaeEquipamentoResumo:
    equipamento: str
    horas_teste: int
    mae_baseline_kw: float
    mae_lightgbm_kw: float
    melhora_pct: float


@dataclass(frozen=True)
class MaeResumo:
    horas_teste: int
    baseline_sazonal_kw: float
    lightgbm_kw: float
    melhora_mediana_pct: float
    ressalva_nowcast: str
    por_equipamento: tuple[MaeEquipamentoResumo, ...]


@dataclass(frozen=True)
class ShapFeatureResumo:
    feature: str
    pct: float


@dataclass(frozen=True)
class ShapEquipamentoResumo:
    equipamento: str
    calendario_pct: float
    historico_pct: float
    feature_dominante: str | None


@dataclass(frozen=True)
class ShapResumo:
    horas_equipamento: int
    calendario_pct: float
    historico_pct: float
    limiar_feature_dominante_pct: float
    por_feature: tuple[ShapFeatureResumo, ...]
    por_equipamento: tuple[ShapEquipamentoResumo, ...]


@dataclass(frozen=True)
class TipoBenchmarkResumo:
    tipo: str
    detectados: int
    eventos: int


@dataclass(frozen=True)
class DetectorBenchmarkResumo:
    detector: str
    por_tipo: tuple[TipoBenchmarkResumo, ...]
    total_detectados: int
    total_eventos: int
    falso_alarme_horas: int
    horas_base: int


@dataclass(frozen=True)
class BenchmarkResumo:
    semente: int
    eventos_por_tipo_por_equipamento: int
    limiar_z: float
    detectores: tuple[DetectorBenchmarkResumo, ...]


@dataclass(frozen=True)
class BaselineFracaResumo:
    criterio: str
    semanas_completas_treino: int


@dataclass(frozen=True)
class ResumoM3:
    sensor_id: str
    dados: DadosResumo
    mae: MaeResumo
    shap: ShapResumo
    benchmark_sintetico: BenchmarkResumo
    baseline_fraca: BaselineFracaResumo


def _mae_por_equipamento(t: ResultadoTreino) -> tuple[MaeEquipamentoResumo, ...]:
    return tuple(
        MaeEquipamentoResumo(
            eq, m.horas_teste, m.mae_baseline, m.mae_modelo, 100.0 * (m.mae_baseline - m.mae_modelo) / m.mae_baseline
        )
        for eq, m in t.metricas.items()
    )


def _mae(t: ResultadoTreino) -> MaeResumo:
    por_eq = _mae_por_equipamento(t)
    horas = np.array([m.horas_teste for m in t.metricas.values()], dtype=float)
    base = np.array([m.mae_baseline for m in t.metricas.values()])
    mod = np.array([m.mae_modelo for m in t.metricas.values()])
    return MaeResumo(
        horas_teste=int(horas.sum()),
        baseline_sazonal_kw=float((base * horas).sum() / horas.sum()),
        lightgbm_kw=float((mod * horas).sum() / horas.sum()),
        melhora_mediana_pct=float(np.median([e.melhora_pct for e in por_eq])),
        ressalva_nowcast=RESSALVA_NOWCAST,
        por_equipamento=por_eq,
    )


def montar_resumo(r: ResultadoM3, fonte: FonteDados) -> ResumoM3:
    p, t, d, b = r.parametros, r.treino, r.deteccao, r.benchmark
    agg = d.d7_agregado
    if agg is None:
        raise ValueError("resumo exige a explicacao SHAP agregada")
    detectores = tuple(
        DetectorBenchmarkResumo(
            detector=nome,
            por_tipo=tuple(
                TipoBenchmarkResumo(tp, b.taxas[nome].detectados.get(tp, 0), b.taxas[nome].injetados.get(tp, 0))
                for tp in TIPOS
            ),
            total_detectados=sum(b.taxas[nome].detectados.get(tp, 0) for tp in TIPOS),
            total_eventos=sum(b.taxas[nome].injetados.get(tp, 0) for tp in TIPOS),
            falso_alarme_horas=b.taxas[nome].alertas_fora,
            horas_base=b.taxas[nome].horas_fora,
        )
        for nome in (TIPO_ZSCORE, TIPO_LIGHTGBM)
    )
    modelos = next(iter(t.modelos.values()))
    return ResumoM3(
        sensor_id=p.sensor_id,
        dados=DadosResumo(
            fonte=fonte.descricao,
            periodo=JanelaResumo(p.inicio, p.fim_teste),
            treino=JanelaResumo(p.inicio, p.fim_treino),
            reservado=JanelaResumo(p.fim_treino, p.fim_teste),
            equipamentos_no_andar=len(t.horas_validas),
            equipamentos_modelados=len(t.modelos),
            equipamentos_sem_carga=tuple(t.sem_carga),
            linhas_minuto=fonte.linhas_minuto,
        ),
        mae=_mae(t),
        shap=ShapResumo(
            horas_equipamento=d.horas_avaliadas,
            calendario_pct=100.0 * agg.participacao_calendario,
            historico_pct=100.0 * agg.participacao_historico,
            limiar_feature_dominante_pct=100.0 * LIMIAR_FEATURE_DOMINANTE,
            por_feature=tuple(ShapFeatureResumo(f, 100.0 * v) for f, v in agg.participacao_por_feature.items()),
            por_equipamento=tuple(
                ShapEquipamentoResumo(eq, 100.0 * c.participacao_calendario, 100.0 * c.participacao_historico, c.feature_dominante)
                for eq, c in d.d7_por_equipamento.items()
            ),
        ),
        benchmark_sintetico=BenchmarkResumo(b.semente, b.por_tipo, b.limiar, detectores),
        baseline_fraca=BaselineFracaResumo(
            criterio=(
                f"menos de {SEMANAS_MINIMAS} semanas completas de treino com pelo menos "
                f"{round(100 * COBERTURA_SEMANA_COMPLETA)}% das horas validas"
            ),
            semanas_completas_treino=modelos.baseline.semanas_completas,
        ),
    )
