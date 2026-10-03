"""Contrato M3 -> API: o que o CLI do M3 grava precisa passar no esquema estrito que a API valida.

Teste de fronteira entre pacotes: roda o ciclo real do M3 (serie sintetica, semente fixa), grava os
artefatos pelo mesmo caminho do CLI (`publicar`) e le com o adaptador da plataforma.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.application.executar_m3 import ExecutarM3, ParametrosM3, ResultadoM3
from mapen_modelos.application.resumo_m3 import FonteDados
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao
from mapen_modelos.domain.features import tipo_dia
from mapen_modelos.infrastructure.lightgbm_modelo import TreinadorLightGBM
from mapen_modelos.infrastructure.shap_explicador import ExplicadorShap
from mapen_modelos.interface.cli import publicar
from mapen_plataforma.infrastructure.resultados_m3_json import ResultadosM3Json

INICIO = pd.Timestamp("2026-02-02")  # segunda-feira
SENSOR = "sintetico"
FIM_TREINO = INICIO + pd.Timedelta(weeks=10)
MEIO = FIM_TREINO + pd.Timedelta(weeks=2)
FIM_TESTE = FIM_TREINO + pd.Timedelta(weeks=4)
EMPRESA = "empresa-demo"
MINUTOS = 123456


class _Leitor:
    def __init__(self, largo: pd.DataFrame) -> None:
        self._largo = largo

    def ler_series_horarias(self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
        return self._largo[(self._largo.index >= inicio) & (self._largo.index < fim)].copy()


def _largo() -> pd.DataFrame:
    idx = pd.date_range(INICIO, periods=168 * 14, freq="1h")
    util = (tipo_dia(idx) < 5) & (idx.hour.to_numpy() >= 8) & (idx.hour.to_numpy() < 18)
    rng = np.random.default_rng(5)
    return pd.DataFrame(
        {
            "ac": np.where(util, 6.0, 0.8) + rng.normal(0, 0.25, len(idx)),
            "luz": np.where(util, 2.0, 0.3) + rng.normal(0, 0.1, len(idx)),
            "inerte": 0.0,
        },
        index=idx,
    )


@pytest.fixture(scope="module")
def executado() -> tuple[ExecutarM3, ResultadoM3]:
    p = ParametrosM3(
        sensor_id=SENSOR, inicio=INICIO, fim_treino=FIM_TREINO, fim_teste=FIM_TESTE, limiar_z=4.0,
        semente=11, eventos_por_tipo=2, equipamento_reducao="ac", fracao_reducao=0.15, meio_do_teste=MEIO,
    )
    m3 = ExecutarM3(_Leitor(_largo()), TreinadorLightGBM(n_arvores=60), ExplicadorShap())
    config = ConfigAvaliacao(treino_inicial=pd.Timedelta(weeks=4), teste=pd.Timedelta(weeks=2))
    return m3, m3.executar(p, config)


def test_cli_grava_resumo_que_a_api_valida(executado: tuple[ExecutarM3, ResultadoM3], tmp_path: Path) -> None:
    m3, resultado = executado
    publicar(m3, resultado, FonteDados("fonte sintetica de teste", MINUTOS), tmp_path)

    assert (tmp_path / "resumo.json").is_file()
    repo = ResultadosM3Json(tmp_path, EMPRESA)
    resumo = repo.resumo(EMPRESA)
    assert resumo is not None
    assert repo.alertas(EMPRESA) is not None
    assert repo.economia(EMPRESA) is not None

    assert resumo.sensor_id == SENSOR
    assert resumo.dados.linhas_minuto == MINUTOS
    assert resumo.dados.equipamentos_sem_carga == ("inerte",)
    assert resumo.dados.equipamentos_modelados == 2
    assert {e.equipamento for e in resumo.mae.por_equipamento} == {"ac", "luz"}


def test_resumo_gravado_traz_os_numeros_do_pipeline(
    executado: tuple[ExecutarM3, ResultadoM3], tmp_path: Path
) -> None:
    m3, resultado = executado
    publicar(m3, resultado, FonteDados("fonte sintetica de teste", MINUTOS), tmp_path)
    resumo = ResultadosM3Json(tmp_path, EMPRESA).resumo(EMPRESA)
    assert resumo is not None

    horas = sum(m.horas_teste for m in resultado.treino.metricas.values())
    mae_mod = sum(m.mae_modelo * m.horas_teste for m in resultado.treino.metricas.values()) / horas
    assert resumo.mae.horas_teste == horas
    assert resumo.mae.lightgbm_kw == pytest.approx(mae_mod, abs=5e-5)
    bench = resultado.benchmark.taxas["zscore"]
    zs = next(d for d in resumo.benchmark_sintetico.detectores if d.detector == "zscore")
    assert zs.total_eventos == sum(bench.injetados.values())
    assert zs.falso_alarme_horas == bench.alertas_fora
    assert resumo.baseline_fraca.semanas_completas_treino > 0
