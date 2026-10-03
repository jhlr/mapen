"""Dono do ciclo do M3: treino e avaliacao, alertas, benchmark sintetico e antes x depois."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mapen_modelos.application.benchmark_sintetico import BenchmarkSintetico, ResultadoBenchmark
from mapen_modelos.application.comparar_antes_depois import (
    CompararAntesDepois,
    ReducaoSintetica,
    ResultadoAntesDepois,
    Varredura,
)
from mapen_modelos.application.detectar_anomalias import DetectarAnomalias, ResultadoDeteccao
from mapen_modelos.application.resumo_m3 import FonteDados, ResumoM3, montar_resumo
from mapen_modelos.application.portas import Explicador, LeitorSeries, TreinadorModelo
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao, ResultadoTreino, TreinarEAvaliar


@dataclass(frozen=True)
class ParametrosM3:
    sensor_id: str
    inicio: pd.Timestamp
    fim_treino: pd.Timestamp  # fim exclusivo da janela de treino/walk-forward
    fim_teste: pd.Timestamp  # fim exclusivo do periodo reservado (deteccao, benchmark, antes x depois)
    limiar_z: float
    semente: int
    eventos_por_tipo: int
    equipamento_reducao: str
    fracao_reducao: float
    meio_do_teste: pd.Timestamp  # fim do "antes" e inicio da reducao sintetica


@dataclass
class ResultadoM3:
    parametros: ParametrosM3
    config: ConfigAvaliacao
    treino: ResultadoTreino
    deteccao: ResultadoDeteccao
    benchmark: ResultadoBenchmark
    antes_depois: ResultadoAntesDepois
    controle: ResultadoAntesDepois
    varredura: Varredura

    @property
    def varredura_recuperado_pct(self) -> dict[str, float]:
        """Recuperado (%) pelo metodo baseline normalizado, um equipamento tratado por vez."""
        return self.varredura.baseline_pct


class ExecutarM3:
    def __init__(self, leitor: LeitorSeries, treinador: TreinadorModelo, explicador: Explicador) -> None:
        self._treinar = TreinarEAvaliar(leitor, treinador)
        self._detectar = DetectarAnomalias(leitor, explicador)
        self._benchmark = BenchmarkSintetico(leitor, self._detectar)
        self._comparar = CompararAntesDepois(leitor)

    def executar(self, p: ParametrosM3, config: ConfigAvaliacao = ConfigAvaliacao()) -> ResultadoM3:
        treino = self._treinar.executar(p.sensor_id, p.inicio, p.fim_treino, config)
        deteccao = self._detectar.executar(p.sensor_id, treino, p.fim_treino, p.fim_teste, p.limiar_z)
        benchmark = self._benchmark.executar(
            p.sensor_id, treino, p.fim_treino, p.fim_teste, p.limiar_z, p.semente, p.eventos_por_tipo
        )
        reducao = ReducaoSintetica(p.equipamento_reducao, p.fracao_reducao, p.meio_do_teste)
        antes_depois = self._comparar.executar(
            p.sensor_id, treino, p.fim_treino, p.meio_do_teste, p.fim_teste, reducao, inicio_pre=p.inicio
        )
        controle = self._comparar.executar(
            p.sensor_id, treino, p.fim_treino, p.meio_do_teste, p.fim_teste, inicio_pre=p.inicio
        )
        varredura = self._comparar.varredura_reducao(
            p.sensor_id, treino, p.fim_treino, p.meio_do_teste, p.fim_teste, p.fracao_reducao, inicio_pre=p.inicio
        )
        return ResultadoM3(p, config, treino, deteccao, benchmark, antes_depois, controle, varredura)

    def resumir(self, resultado: ResultadoM3, fonte: FonteDados) -> ResumoM3:
        """Resumo do ciclo para o dashboard; o `ExecutarM3` e o dono de tudo que o M3 publica."""
        return montar_resumo(resultado, fonte)
