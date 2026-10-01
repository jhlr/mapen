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
    EconomiaM3,
    Janela,
    MaeEquipamento,
    MaeModelos,
    ParticipacaoFeature,
    ReducaoSintetica,
    ResumoM3,
    ResumoShap,
    ShapEquipamento,
    TipoAlerta,
)
from mapen_plataforma.domain.tempo import de_local_ingenuo

ARQUIVO_RESUMO = "resumo.json"
ARQUIVO_ALERTAS = "alertas.json"
ARQUIVO_ECONOMIA = "economia.json"
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


class _Resumo(_Modelo):
    versao_esquema: Literal[1]
    sensor_id: Texto
    dados: _Dados
    mae: _Mae
    shap: _Shap
    benchmark_sintetico: _Benchmark
    baseline_fraca: _BaselineFraca

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
    equipamentos: list[_EconomiaEq]

    def dominio(self) -> EconomiaM3:
        r = self.reducao_sintetica
        if r.equipamento not in {e.equipamento for e in self.equipamentos}:
            raise ValueError("equipamento da reducao ausente da lista")
        return EconomiaM3(
            self.sensor_id, self.natureza, self.aviso, self.periodo_antes.dominio(), self.periodo_depois.dominio(),
            ReducaoSintetica(r.equipamento, r.fracao_pct, _local(r.a_partir_de)),
            self.recuperado_pct, self.tolerancia_pp, self.dentro_da_tolerancia,
            tuple(
                EconomiaEquipamento(
                    e.equipamento, e.kwh_antes, e.kwh_depois, e.kwh_contrafactual, e.economia_kwh, e.economia_pct,
                    e.economia_pct_sem_reducao, e.recuperado_pct_com_reducao_sintetica,
                    e.reducao_sintetica_aplicada, e.baseline_fraca,
                )
                for e in self.equipamentos
            ),
        )


_M = TypeVar("_M", _Resumo, _Alertas, _Economia)
_T = TypeVar("_T", ResumoM3, AlertasM3, EconomiaM3)


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
