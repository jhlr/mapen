"""Adaptador de `ResultadosM3Repositorio` sobre os JSON de `data/m3/` (artefatos do M3).

- Os artefatos do demo pertencem so a empresa dona (`empresa_dona`); outra empresa recebe `None`.
- Nomes de arquivo fixos dentro de um diretorio configurado; o caminho resolvido (seguindo links)
  precisa continuar dentro do diretorio, senao o artefato e tratado como indisponivel.
- Esquema validado de forma estrita (campo desconhecido, tipo errado, NaN ou versao diferente
  recusam o arquivo inteiro); a mensagem de erro nao ecoa o conteudo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, NaiveDatetime

from mapen_plataforma.application.portas import ResultadosM3Indisponiveis
from mapen_plataforma.domain.resultados_m3 import (
    AlertaM3,
    AlertasM3,
    BenchmarkSintetico,
    ContribuicaoShap,
    CriterioBaselineFraca,
    DadosSubconjunto,
    DeteccaoPorTipo,
    DetectorSintetico,
    EconomiaEquipamento,
    BenchmarkPrevisao,
    DecisaoPrevisao,
    EconomiaM3,
    EstudoPrevisao,
    Janela,
    MaeEquipamento,
    MaeModelos,
    MaseEquipamento,
    ModeloPrevisao,
    ParticipacaoFeature,
    ReducaoSintetica,
    ResumoM3,
    ResumoShap,
    ShapEquipamento,
    ShapPrevisao,
    TipoAlerta,
)
from mapen_plataforma.domain.tempo import de_local_ingenuo

ARQUIVO_RESUMO = "resumo.json"
ARQUIVO_ALERTAS = "alertas.json"
ARQUIVO_ECONOMIA = "economia.json"
ARQUIVO_PREVISAO = "previsao.json"
TAMANHO_MAX_ARTEFATO = 16 * 1024 * 1024
VERSAO_ESQUEMA = 1

Finito = Annotated[float, Field(allow_inf_nan=False)]
Texto = Annotated[str, Field(min_length=1, max_length=512)]
Contagem = Annotated[int, Field(ge=0)]
Pct = Annotated[float, Field(allow_inf_nan=False, ge=0)]


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class _Janela(_Modelo):
    inicio: NaiveDatetime
    fim: NaiveDatetime

    def dominio(self) -> Janela:
        return Janela(de_local_ingenuo(self.inicio), de_local_ingenuo(self.fim))


def _local(t: datetime) -> datetime:
    return de_local_ingenuo(t)


# ---------------------------------------------------------------- resumo.json


class _Dados(_Modelo):
    fonte: Texto
    periodo: _Janela
    treino: _Janela
    reservado: _Janela
    equipamentos_no_andar: Contagem
    equipamentos_modelados: Contagem
    equipamentos_sem_carga: list[Texto]
    linhas_minuto: Contagem


class _MaeEq(_Modelo):
    equipamento: Texto
    horas_teste: Contagem
    mae_baseline_kw: Finito
    mae_lightgbm_kw: Finito
    melhora_pct: Finito


class _Mae(_Modelo):
    unidade: Literal["kW"]
    horas_teste: Contagem
    baseline_sazonal: Finito
    lightgbm: Finito
    melhora_mediana_pct: Finito
    ressalva_nowcast: Texto
    por_equipamento: list[_MaeEq]


class _Feature(_Modelo):
    feature: Texto
    pct: Pct


class _ShapEq(_Modelo):
    equipamento: Texto
    calendario_pct: Pct
    historico_pct: Pct
    feature_dominante: Texto | None


class _Shap(_Modelo):
    horas_equipamento: Contagem
    calendario_pct: Pct
    historico_pct: Pct
    limiar_feature_dominante_pct: Pct
    por_feature: list[_Feature]
    por_equipamento: list[_ShapEq]


class _PorTipo(_Modelo):
    tipo: Texto
    detectados: Contagem
    eventos: Contagem


class _Detector(_Modelo):
    detector: Literal["zscore", "lightgbm"]
    por_tipo: list[_PorTipo]
    total_detectados: Contagem
    total_eventos: Contagem
    falso_alarme_horas: Contagem
    horas_base: Contagem


class _Benchmark(_Modelo):
    semente: int
    eventos_por_tipo_por_equipamento: Contagem
    limiar_z: Finito
    detectores: list[_Detector]


class _BaselineFraca(_Modelo):
    criterio: Texto
    semanas_completas_treino: Contagem


class _MetodoAntesDepois(_Modelo):
    metodo: Texto
    recuperado_pct_alvo: Finito | None
    dentro_da_tolerancia_alvo: bool
    equipamentos_avaliados: int
    equipamentos_dentro_da_tolerancia: int
    equipamentos_sem_resultado: list[Texto]
    erro_abs_mediano_pp: Finito | None
    erro_abs_maximo_pp: Finito | None


class _AntesDepoisResumo(_Modelo):
    equipamento_alvo: Texto
    injetado_pct: Finito
    tolerancia_pp: Annotated[float, Field(allow_inf_nan=False, gt=0)]
    metodos: list[_MetodoAntesDepois]


class _Resumo(_Modelo):
    versao_esquema: Literal[1]
    sensor_id: Texto
    dados: _Dados
    mae: _Mae
    shap: _Shap
    benchmark_sintetico: _Benchmark
    baseline_fraca: _BaselineFraca
    antes_depois: _AntesDepoisResumo | None = None  # opcional: totais dos dois metodos; o detalhe vai em /economia

    def dominio(self) -> ResumoM3:
        d, m, s, b = self.dados, self.mae, self.shap, self.benchmark_sintetico
        return ResumoM3(
            sensor_id=self.sensor_id,
            dados=DadosSubconjunto(
                d.fonte, d.periodo.dominio(), d.treino.dominio(), d.reservado.dominio(),
                d.equipamentos_no_andar, d.equipamentos_modelados, tuple(d.equipamentos_sem_carga), d.linhas_minuto,
            ),
            mae=MaeModelos(
                m.horas_teste, m.baseline_sazonal, m.lightgbm, m.melhora_mediana_pct, m.ressalva_nowcast,
                tuple(
                    MaeEquipamento(x.equipamento, x.horas_teste, x.mae_baseline_kw, x.mae_lightgbm_kw, x.melhora_pct)
                    for x in m.por_equipamento
                ),
            ),
            shap=ResumoShap(
                s.horas_equipamento, s.calendario_pct, s.historico_pct, s.limiar_feature_dominante_pct,
                tuple(ParticipacaoFeature(f.feature, f.pct) for f in s.por_feature),
                tuple(
                    ShapEquipamento(e.equipamento, e.calendario_pct, e.historico_pct, e.feature_dominante)
                    for e in s.por_equipamento
                ),
            ),
            benchmark_sintetico=BenchmarkSintetico(
                b.semente, b.eventos_por_tipo_por_equipamento, b.limiar_z,
                tuple(
                    DetectorSintetico(
                        x.detector,
                        tuple(DeteccaoPorTipo(t.tipo, t.detectados, t.eventos) for t in x.por_tipo),
                        x.total_detectados, x.total_eventos, x.falso_alarme_horas, x.horas_base,
                    )
                    for x in b.detectores
                ),
            ),
            baseline_fraca=CriterioBaselineFraca(self.baseline_fraca.criterio, self.baseline_fraca.semanas_completas_treino),
        )


# ---------------------------------------------------------------- alertas.json


class _Contribuicao(_Modelo):
    feature: Texto
    shap: Finito


class _Alerta(_Modelo):
    equipamento: Texto
    timestamp: NaiveDatetime
    tipo: Literal["zscore", "lightgbm"]
    esperado_kw: Finito
    observado_kw: Finito
    z: Finito
    janela_baseline: _Janela
    top_shap: list[_Contribuicao] | None
    baseline_fraca: bool
    status: Literal["candidato_nao_corroborado"]

    def dominio(self) -> AlertaM3:
        tipo: TipoAlerta = self.tipo
        return AlertaM3(
            self.equipamento, _local(self.timestamp), tipo, self.esperado_kw, self.observado_kw, self.z,
            self.janela_baseline.dominio(),
            None if self.top_shap is None else tuple(ContribuicaoShap(c.feature, c.shap) for c in self.top_shap),
            self.baseline_fraca,
        )


class _Alertas(_Modelo):
    versao_esquema: Literal[1]
    sensor_id: Texto
    periodo: _Janela
    limiar_z: Finito
    aviso: Texto
    alertas: list[_Alerta]

    def dominio(self) -> AlertasM3:
        for a in self.alertas:
            if (a.tipo == "lightgbm") != (a.top_shap is not None):
                raise ValueError("top_shap so existe em alerta lightgbm")
        return AlertasM3(
            self.sensor_id, self.periodo.dominio(), self.limiar_z, self.aviso,
            tuple(a.dominio() for a in self.alertas),
        )


# ---------------------------------------------------------------- economia.json


class _EconomiaEq(_Modelo):
    equipamento: Texto
    kwh_antes: Finito
    kwh_depois: Finito
    kwh_contrafactual: Finito | None
    economia_kwh: Finito | None
    economia_pct: Finito | None
    economia_pct_sem_reducao: Finito | None
    recuperado_pct_com_reducao_sintetica: Finito | None
    reducao_sintetica_aplicada: bool
    baseline_fraca: bool
    recuperado_pct_controle: Finito | None = None
    economia_pct_controle_sem_reducao: Finito | None = None
    controles_usados: list[Texto] | None = None


class _Reducao(_Modelo):
    equipamento: Texto
    fracao_pct: Finito
    a_partir_de: NaiveDatetime


class _Economia(_Modelo):
    versao_esquema: Literal[1]
    sensor_id: Texto
    natureza: Literal["validacao_de_metodo_sintetica"]
    aviso: Texto
    periodo_antes: _Janela
    periodo_depois: _Janela
    reducao_sintetica: _Reducao
    recuperado_pct: Finito | None
    tolerancia_pp: Annotated[float, Field(allow_inf_nan=False, gt=0)]
    dentro_da_tolerancia: bool
    metodo_recuperado_pct: Literal["baseline_normalizado"] | None = None
    metodo_controle: Literal["diferenca_em_diferencas_grupo_controle"] | None = None
    recuperado_pct_controle: Finito | None = None
    dentro_da_tolerancia_controle: bool | None = None
    equipamentos: list[_EconomiaEq]

    def dominio(self) -> EconomiaM3:
        r = self.reducao_sintetica
        if r.equipamento not in {e.equipamento for e in self.equipamentos}:
            raise ValueError("equipamento da reducao ausente da lista")
        tem_controle = self.dentro_da_tolerancia_controle is not None
        if tem_controle != (self.metodo_controle is not None) or any(
            (e.controles_usados is not None) != tem_controle for e in self.equipamentos
        ):
            raise ValueError("metodo de controle so existe completo: nome, veredito do alvo e controles por equipamento")
        return EconomiaM3(
            self.sensor_id, self.natureza, self.aviso, self.periodo_antes.dominio(), self.periodo_depois.dominio(),
            ReducaoSintetica(r.equipamento, r.fracao_pct, _local(r.a_partir_de)),
            self.recuperado_pct, self.tolerancia_pp, self.dentro_da_tolerancia,
            tuple(
                EconomiaEquipamento(
                    e.equipamento, e.kwh_antes, e.kwh_depois, e.kwh_contrafactual, e.economia_kwh, e.economia_pct,
                    e.economia_pct_sem_reducao, e.recuperado_pct_com_reducao_sintetica,
                    e.reducao_sintetica_aplicada, e.baseline_fraca,
                    e.recuperado_pct_controle, e.economia_pct_controle_sem_reducao,
                    None if e.controles_usados is None else tuple(e.controles_usados),
                )
                for e in self.equipamentos
            ),
            self.recuperado_pct_controle, self.dentro_da_tolerancia_controle,
        )


# ---------------------------------------------------------------- previsao.json

Nulavel = Finito | None


class _Protocolo(_Modelo):
    origem: Texto
    horizonte_h: Annotated[int, Field(ge=1)]
    defasagem_minima_h: Annotated[int, Field(ge=1)]
    treino: _Janela
    reservado: _Janela
    dobras_walk_forward: Contagem
    referencia_mase: Texto


class _MetricaPrevisao(_Modelo):
    mae_kw: Nulavel
    rmse_kw: Nulavel
    mase: Nulavel
    horas: Contagem


class _Decisao(_Modelo):
    regra_aplicada: Texto
    adotado: Texto
    passaram_regra_de_ganho: list[Texto]
    melhor_mediana: Texto
    motivo: Annotated[str, Field(min_length=1, max_length=2048)]


class _ShapPrevisao(_Modelo):
    participacao_por_feature: dict[Texto, Nulavel]
    participacao_por_grupo: dict[Texto, Nulavel]
    d7_feature_dominante: Texto | None
    d7_flag: bool
    equipamentos_com_flag: list[Texto]
    horas: Contagem


class _BenchmarkPrevisao(_Modelo):
    sintetico: Literal[True]
    previsor: Texto
    semente: int
    eventos_por_tipo_por_equipamento: Contagem
    limiar_z: Finito
    injetados: dict[Texto, Contagem]
    detectados: dict[Texto, Contagem]
    taxa_deteccao: Nulavel
    taxa_deteccao_por_tipo: dict[Texto, Nulavel]
    alertas_fora_da_zona: Contagem
    horas_fora_da_zona: Contagem
    taxa_falso_alarme: Nulavel


class _Previsao(_Modelo):
    versao_esquema: Literal[1]
    sensor_id: Texto
    natureza: Literal["estudo_previsao_dia_seguinte"]
    aviso: Annotated[str, Field(min_length=1, max_length=1024)]
    protocolo: _Protocolo
    equipamentos: list[Texto]
    sem_carga: list[Texto]
    modelos: list[Texto]
    metricas_reservado: dict[Texto, dict[Texto, _MetricaPrevisao]]
    mae_agregado_kw: dict[Texto, Nulavel]
    mediana_mase_reservado: dict[Texto, Nulavel]
    mediana_mase_desenvolvimento: dict[Texto, Nulavel]
    vitorias_vs_naive168: dict[Texto, Contagem]
    vitorias_melhor_de_todos: dict[Texto, Contagem]
    decisao: _Decisao
    mase_por_equipamento: dict[Texto, dict[Texto, Nulavel]]
    avisos: list[Annotated[str, Field(max_length=1024)]]
    shap_lightgbm: _ShapPrevisao | None
    benchmark_sintetico: _BenchmarkPrevisao | None

    def dominio(self) -> EstudoPrevisao:
        nomes = set(self.modelos)
        referencias = (
            self.mae_agregado_kw, self.mediana_mase_reservado, self.mediana_mase_desenvolvimento,
            self.vitorias_melhor_de_todos, self.mase_por_equipamento,
        )
        if any(set(r) != nomes for r in referencias) or set(self.metricas_reservado) != nomes:
            raise ValueError("previsao: modelos inconsistentes entre as tabelas")
        if not set(self.vitorias_vs_naive168) <= nomes:
            raise ValueError("previsao: vitorias de modelo desconhecido")
        d = self.decisao
        if d.adotado not in nomes or d.melhor_mediana not in nomes or not set(d.passaram_regra_de_ganho) <= nomes:
            raise ValueError("previsao: decisao cita modelo desconhecido")
        p = self.protocolo
        b = self.benchmark_sintetico
        s = self.shap_lightgbm
        eq = tuple(self.equipamentos)
        if any(set(por_eq) != set(eq) for por_eq in self.mase_por_equipamento.values()):
            raise ValueError("previsao: MASE por equipamento nao cobre a lista de equipamentos")
        return EstudoPrevisao(
            sensor_id=self.sensor_id, aviso=self.aviso, horizonte_h=p.horizonte_h, defasagem_minima_h=p.defasagem_minima_h,
            treino=p.treino.dominio(), reservado=p.reservado.dominio(), dobras_walk_forward=p.dobras_walk_forward,
            referencia_mase=p.referencia_mase, equipamentos=eq, sem_carga=tuple(self.sem_carga),
            modelos=tuple(
                ModeloPrevisao(
                    m, self.mae_agregado_kw[m], self.mediana_mase_reservado[m], self.mediana_mase_desenvolvimento.get(m),
                    self.vitorias_vs_naive168.get(m), self.vitorias_melhor_de_todos[m],
                )
                for m in self.modelos
            ),
            mase_por_equipamento=tuple(
                MaseEquipamento(e, {m: self.mase_por_equipamento[m][e] for m in self.modelos}) for e in eq
            ),
            decisao=DecisaoPrevisao(
                d.regra_aplicada, d.adotado, tuple(d.passaram_regra_de_ganho), d.melhor_mediana, d.motivo
            ),
            avisos=tuple(self.avisos),
            shap=None if s is None else ShapPrevisao(
                dict(s.participacao_por_grupo), dict(s.participacao_por_feature), s.d7_feature_dominante,
                tuple(s.equipamentos_com_flag), s.horas,
            ),
            benchmark=None if b is None else BenchmarkPrevisao(
                b.previsor, b.semente, b.eventos_por_tipo_por_equipamento, b.limiar_z, dict(b.injetados),
                dict(b.detectados), b.alertas_fora_da_zona, b.horas_fora_da_zona,
            ),
        )


_M = TypeVar("_M", _Resumo, _Alertas, _Economia, _Previsao)
_T = TypeVar("_T", ResumoM3, AlertasM3, EconomiaM3, EstudoPrevisao)


class ResultadosM3Json:
    """Le os artefatos sob demanda (sao pequenos); `empresa_dona` e a unica que os enxerga."""

    def __init__(self, diretorio: Path, empresa_dona: str) -> None:
        self._base = diretorio
        self._dona = empresa_dona

    def _ler(self, nome: str, modelo: type[_M], converter: Callable[[_M], _T]) -> _T:
        base = self._base.resolve()
        try:
            alvo = (base / nome).resolve(strict=True)
            if not alvo.is_relative_to(base) or not alvo.is_file():
                raise ResultadosM3Indisponiveis(f"artefato {nome} fora do diretorio de resultados")
            if alvo.stat().st_size > TAMANHO_MAX_ARTEFATO:
                raise ResultadosM3Indisponiveis(f"artefato {nome} grande demais")
            bruto = alvo.read_bytes()
        except (FileNotFoundError, NotADirectoryError):
            raise ResultadosM3Indisponiveis(f"artefato {nome} ausente") from None
        except OSError:
            raise ResultadosM3Indisponiveis(f"artefato {nome} ilegivel") from None
        try:
            return converter(modelo.model_validate_json(bruto))
        except ValueError:  # ValidationError e subclasse de ValueError
            raise ResultadosM3Indisponiveis(f"artefato {nome} fora do esquema v{VERSAO_ESQUEMA}") from None

    def resumo(self, empresa_id: str) -> ResumoM3 | None:
        if empresa_id != self._dona:
            return None
        return self._ler(ARQUIVO_RESUMO, _Resumo, _Resumo.dominio)

    def alertas(self, empresa_id: str) -> AlertasM3 | None:
        if empresa_id != self._dona:
            return None
        return self._ler(ARQUIVO_ALERTAS, _Alertas, _Alertas.dominio)

    def economia(self, empresa_id: str) -> EconomiaM3 | None:
        if empresa_id != self._dona:
            return None
        return self._ler(ARQUIVO_ECONOMIA, _Economia, _Economia.dominio)

    def previsao(self, empresa_id: str) -> EstudoPrevisao | None:
        if empresa_id != self._dona:
            return None
        return self._ler(ARQUIVO_PREVISAO, _Previsao, _Previsao.dominio)
