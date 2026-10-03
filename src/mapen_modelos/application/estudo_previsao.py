"""Caso de uso EstudoPrevisao: compara previsores do dia seguinte e aplica a regra pre-registrada.

Dono do ciclo: avalia cada previsor por equipamento nas dobras walk-forward (desenvolvimento) e
no periodo reservado (decisao), aplica `decidir_adocao`, mede o SHAP do previsor explicavel e
chama o benchmark sintetico com os residuos do previsor adotado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from mapen_modelos.application.benchmark_previsao import BenchmarkPrevisao, ResultadoBenchmarkPrevisao
from mapen_modelos.application.portas import LeitorSeries, Previsor, PrevisorExplicavel
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao
from mapen_modelos.domain.baseline import PISO_DESVIO_ABSOLUTO_KW, PISO_DESVIO_RELATIVO
from mapen_modelos.domain.explica import LIMIAR_FEATURE_DOMINANTE
from mapen_modelos.domain.injecao import equipamento_com_carga
from mapen_modelos.domain.metricas_previsao import (
    NAIVE_168,
    Decisao,
    Metricas,
    decidir_adocao,
    escala_mase,
    metricas,
    participacao_por_grupo,
    suporte_comum,
)
from mapen_modelos.domain.previsao import FEATURES_PREVISAO, HORIZONTE_H
from mapen_modelos.domain.validacao import Dobra, dobras_walk_forward, verificar_sem_vazamento

CORTE_MINIMO_KW = 0.0


@dataclass(frozen=True)
class ParametrosPrevisao:
    sensor_id: str
    inicio: pd.Timestamp
    fim_treino: pd.Timestamp
    fim_teste: pd.Timestamp
    limiar_z: float
    semente: int
    eventos_por_tipo: int


@dataclass(frozen=True)
class ShapPrevisao:
    participacao_por_feature: dict[str, float]
    participacao_por_grupo: dict[str, float]
    feature_dominante: str | None
    equipamentos_com_flag: list[str]
    horas: int


@dataclass
class ResultadoPrevisao:
    parametros: ParametrosPrevisao
    dobras: list[Dobra]
    equipamentos: list[str]
    sem_carga: list[str]
    modelos: list[str]
    escala: dict[str, float]
    reservado: dict[str, dict[str, Metricas]]
    desenvolvimento: dict[str, dict[str, float]]  # modelo -> equipamento -> MASE medio das dobras
    sigma_dobras: dict[str, dict[str, float]]  # modelo -> equipamento -> desvio do residuo (kW)
    decisao: Decisao
    mae_agregado: dict[str, float]
    shap: ShapPrevisao | None
    benchmark: ResultadoBenchmarkPrevisao | None
    avisos: list[str] = field(default_factory=list)

    def mase_reservado(self) -> dict[str, dict[str, float]]:
        return {m: {e: x.mase for e, x in por_eq.items()} for m, por_eq in self.reservado.items()}


def _indice_dias(inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DatetimeIndex:
    if (fim - inicio) % pd.Timedelta(hours=HORIZONTE_H) != pd.Timedelta(0):
        raise ValueError("alvo deve ser composto de dias inteiros")
    return pd.date_range(inicio, fim, freq="1h", inclusive="left")


def _prever(previsor: Previsor, serie: pd.Series, treino_fim: pd.Timestamp, alvo: pd.DatetimeIndex) -> np.ndarray:
    """Previsao truncada em 0 kW (potencia nao e negativa); NaN permanece NaN."""
    previsto = previsor.prever(serie, treino_fim, alvo).reindex(alvo).to_numpy(dtype=np.float64)
    return np.asarray(np.maximum(previsto, CORTE_MINIMO_KW), dtype=np.float64)


class EstudoPrevisao:
    def __init__(
        self,
        leitor: LeitorSeries,
        previsores: Sequence[Previsor],
        ordem_simplicidade: tuple[str, ...],
        explicavel: PrevisorExplicavel | None = None,
    ) -> None:
        nomes = tuple(p.nome for p in previsores)
        if set(nomes) != set(ordem_simplicidade) or NAIVE_168 not in nomes:
            raise ValueError("ordem_simplicidade deve listar os previsores e incluir a referencia")
        self._leitor = leitor
        self._previsores = list(previsores)
        self._ordem = ordem_simplicidade
        self._explicavel = explicavel
        self._benchmark = BenchmarkPrevisao()

    def executar(
        self, p: ParametrosPrevisao, config: ConfigAvaliacao = ConfigAvaliacao()
    ) -> ResultadoPrevisao:
        series = self._leitor.ler_series_horarias(p.sensor_id, p.inicio, p.fim_teste)
        dobras = dobras_walk_forward(p.inicio, p.fim_treino, config.treino_inicial, config.teste)
        if not dobras:
            raise ValueError("janela curta demais para uma dobra walk-forward")
        verificar_sem_vazamento(dobras)
        nomes = [pr.nome for pr in self._previsores]
        treino_idx = pd.DatetimeIndex(series.index) < p.fim_treino
        equipamentos = [
            str(e) for e in series.columns if equipamento_com_carga(series.loc[treino_idx, e])
        ]
        sem_carga = [str(e) for e in series.columns if str(e) not in equipamentos]
        alvo_res = _indice_dias(p.fim_treino, p.fim_teste)
        escala: dict[str, float] = {}
        reservado: dict[str, dict[str, Metricas]] = {n: {} for n in nomes}
        desenvolvimento: dict[str, dict[str, float]] = {n: {} for n in nomes}
        sigma: dict[str, dict[str, float]] = {n: {} for n in nomes}
        erros_agregados: dict[str, list[np.ndarray]] = {n: [] for n in nomes}
        for eq in equipamentos:
            serie = series[eq]
            escala[eq] = escala_mase(serie[serie.index < p.fim_treino])
            self._avaliar_reservado(serie, eq, p, alvo_res, escala[eq], reservado, erros_agregados)
            self._avaliar_dobras(serie, eq, dobras, desenvolvimento, sigma)
        mase = {n: {e: reservado[n][e].mase for e in equipamentos} for n in nomes}
        decisao = decidir_adocao(mase, self._ordem)
        mae_agregado = {
            n: float(np.concatenate(erros_agregados[n]).mean()) if erros_agregados[n] else float("nan")
            for n in nomes
        }
        shap = self._shap(series, equipamentos, p, alvo_res)
        adotado = next(pr for pr in self._previsores if pr.nome == decisao.adotado)
        benchmark = self._benchmark.executar(
            series, adotado, sigma[decisao.adotado], p.fim_treino, p.fim_teste,
            p.limiar_z, p.semente, p.eventos_por_tipo,
        )
        return ResultadoPrevisao(
            p, dobras, equipamentos, sem_carga, nomes, escala, reservado, desenvolvimento, sigma,
            decisao, mae_agregado, shap, benchmark,
        )

    def _avaliar_reservado(
        self,
        serie: pd.Series,
        eq: str,
        p: ParametrosPrevisao,
        alvo: pd.DatetimeIndex,
        escala: float,
        reservado: dict[str, dict[str, Metricas]],
        erros: dict[str, list[np.ndarray]],
    ) -> None:
        y = serie.reindex(alvo).to_numpy(dtype=np.float64)
        previsoes = {pr.nome: _prever(pr, serie, p.fim_treino, alvo) for pr in self._previsores}
        ok = suporte_comum(y, previsoes)
        for nome, previsto in previsoes.items():
            reservado[nome][eq] = metricas(y[ok], previsto[ok], escala)
            erros[nome].append(np.abs(y[ok] - previsto[ok]))

    def _avaliar_dobras(
        self,
        serie: pd.Series,
        eq: str,
        dobras: list[Dobra],
        desenvolvimento: dict[str, dict[str, float]],
        sigma: dict[str, dict[str, float]],
    ) -> None:
        mase_dobra: dict[str, list[tuple[float, int]]] = {pr.nome: [] for pr in self._previsores}
        residuos: dict[str, list[np.ndarray]] = {pr.nome: [] for pr in self._previsores}
        for d in dobras:
            alvo = _indice_dias(d.teste_inicio, d.teste_fim)
            esc = escala_mase(serie[serie.index < d.treino_fim])
            y = serie.reindex(alvo).to_numpy(dtype=np.float64)
            previsoes = {pr.nome: _prever(pr, serie, d.treino_fim, alvo) for pr in self._previsores}
            ok = suporte_comum(y, previsoes)
            for nome, previsto in previsoes.items():
                m = metricas(y[ok], previsto[ok], esc)
                mase_dobra[nome].append((m.mase, m.horas))
                residuos[nome].append(y[ok] - previsto[ok])
        media = float(serie.mean())
        piso = max(PISO_DESVIO_RELATIVO * abs(media), PISO_DESVIO_ABSOLUTO_KW)
        for nome in mase_dobra:
            pares = mase_dobra[nome]
            horas = sum(h for _, h in pares)
            desenvolvimento[nome][eq] = sum(m * h for m, h in pares) / horas if horas else float("nan")
            todo = np.concatenate(residuos[nome])
            sigma[nome][eq] = max(float(todo.std(ddof=1)), piso)

    def _shap(
        self, series: pd.DataFrame, equipamentos: list[str], p: ParametrosPrevisao, alvo: pd.DatetimeIndex
    ) -> ShapPrevisao | None:
        if self._explicavel is None:
            return None
        blocos: list[np.ndarray] = []
        com_flag: list[str] = []
        for eq in equipamentos:
            serie = series[eq]
            contrib = self._explicavel.contribuicoes(serie, p.fim_treino, alvo)[list(FEATURES_PREVISAO)]
            valido = serie.reindex(alvo).notna().to_numpy()
            valores = contrib.to_numpy(dtype=np.float64)[valido]
            blocos.append(valores)
            por_eq = np.abs(valores).mean(axis=0)
            if por_eq.sum() > 0 and float(por_eq.max() / por_eq.sum()) > LIMIAR_FEATURE_DOMINANTE:
                com_flag.append(eq)
        todo = np.vstack(blocos)
        media_abs = np.abs(todo).mean(axis=0)
        total = float(media_abs.sum())
        por_feature = {f: float(v / total) for f, v in zip(FEATURES_PREVISAO, media_abs, strict=True)}
        maior = max(por_feature, key=lambda k: por_feature[k])
        dominante = maior if por_feature[maior] > LIMIAR_FEATURE_DOMINANTE else None
        return ShapPrevisao(por_feature, participacao_por_grupo(por_feature), dominante, com_flag, int(todo.shape[0]))

