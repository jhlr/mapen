"""Integracao do M3 sobre series sinteticas (semente fixa): leitura -> treino -> alertas -> benchmark -> antes x depois."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.application.detectar_anomalias import TIPO_LIGHTGBM, TIPO_ZSCORE
from mapen_modelos.application.executar_m3 import ExecutarM3, ParametrosM3, ResultadoM3
from mapen_modelos.application.portas import Regressor
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao, TreinarEAvaliar
from mapen_modelos.domain.features import FEATURES, tipo_dia
from mapen_modelos.domain.validacao import verificar_sem_vazamento
from mapen_modelos.infrastructure.lightgbm_modelo import TreinadorLightGBM
from mapen_modelos.infrastructure.shap_explicador import ExplicadorShap

INICIO = pd.Timestamp("2026-02-02")  # segunda-feira
SENSOR = "sintetico"
FIM_TREINO = INICIO + pd.Timedelta(weeks=10)
MEIO = FIM_TREINO + pd.Timedelta(weeks=2)
FIM_TESTE = FIM_TREINO + pd.Timedelta(weeks=4)
CONFIG = ConfigAvaliacao(treino_inicial=pd.Timedelta(weeks=4), teste=pd.Timedelta(weeks=2))


class LeitorEmMemoria:
    """Implementa a porta `LeitorSeries` sobre um DataFrame largo."""

    def __init__(self, largo: pd.DataFrame) -> None:
        self.largo = largo

    def ler_series_horarias(self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
        assert sensor_id == SENSOR
        return self.largo[(self.largo.index >= inicio) & (self.largo.index < fim)].copy()


def _largo(semanas: int = 14, semente: int = 5, lacuna: bool = True) -> pd.DataFrame:
    """Dois equipamentos com carga (sazonais) e um sem carga; feriados seguem o padrao de domingo."""
    idx = pd.date_range(INICIO, periods=168 * semanas, freq="1h")
    util = (tipo_dia(idx) < 5) & (idx.hour.to_numpy() >= 8) & (idx.hour.to_numpy() < 18)
    rng = np.random.default_rng(semente)
    ac = np.where(util, 6.0, 0.8) + rng.normal(0, 0.25, len(idx))
    luz = np.where(util, 2.0, 0.3) + rng.normal(0, 0.1, len(idx))
    quadro = pd.DataFrame({"ac": ac, "luz": luz, "inerte": 0.0}, index=idx)
    if lacuna:
        quadro.loc[idx[500:506], "ac"] = np.nan  # 6 h ausentes
    return quadro


def _parametros() -> ParametrosM3:
    return ParametrosM3(
        sensor_id=SENSOR, inicio=INICIO, fim_treino=FIM_TREINO, fim_teste=FIM_TESTE, limiar_z=4.0,
        semente=11, eventos_por_tipo=2, equipamento_reducao="ac", fracao_reducao=0.15, meio_do_teste=MEIO,
    )


def _executar(largo: pd.DataFrame) -> ResultadoM3:
    return ExecutarM3(LeitorEmMemoria(largo), TreinadorLightGBM(n_arvores=60), ExplicadorShap()).executar(
        _parametros(), CONFIG
    )


@pytest.fixture(scope="module")
def resultado() -> ResultadoM3:
    return _executar(_largo())


def test_equipamento_sem_carga_fica_fora_dos_modelos(resultado: ResultadoM3) -> None:
    assert resultado.treino.sem_carga == ["inerte"]
    assert set(resultado.treino.modelos) == {"ac", "luz"}


def test_dobras_do_pipeline_nao_vazam(resultado: ResultadoM3) -> None:
    verificar_sem_vazamento(resultado.treino.dobras)
    assert len(resultado.treino.dobras) == 3
    assert all(d.teste_fim <= FIM_TREINO for d in resultado.treino.dobras)


def test_mae_do_lightgbm_nao_e_pior_que_o_baseline_em_serie_sazonal_simples(resultado: ResultadoM3) -> None:
    for m in resultado.treino.metricas.values():
        assert m.mae_baseline < 0.4  # ruido sd 0.25 => MAE ~0.2
        assert m.mae_modelo < 0.4


def test_metricas_da_dobra_zero_nao_dependem_do_futuro() -> None:
    """Vazamento a nivel de modelo: trocar dados depois do teste da dobra 0 nao muda as metricas dela."""
    original = _largo()
    adulterado = original.copy()
    fim_dobra0 = INICIO + CONFIG.treino_inicial + CONFIG.teste
    adulterado.loc[adulterado.index >= fim_dobra0, ["ac", "luz"]] *= 3.0
    a = TreinarEAvaliar(LeitorEmMemoria(original), TreinadorLightGBM(n_arvores=30)).executar(
        SENSOR, INICIO, FIM_TREINO, CONFIG
    )
    b = TreinarEAvaliar(LeitorEmMemoria(adulterado), TreinadorLightGBM(n_arvores=30)).executar(
        SENSOR, INICIO, FIM_TREINO, CONFIG
    )
    for eq in ("ac", "luz"):
        assert a.metricas[eq].por_dobra[0] == b.metricas[eq].por_dobra[0]
        assert a.metricas[eq].por_dobra[2] != b.metricas[eq].por_dobra[2]


class _EspiaoTreinador:
    """Registra o que o treinador recebe; devolve uma media constante."""

    def __init__(self) -> None:
        self.vistos: list[tuple[pd.DataFrame, pd.Series]] = []

    def treinar(self, x: pd.DataFrame, y: pd.Series) -> Regressor:
        self.vistos.append((x, y))
        media = float(y.mean())

        class _Constante:
            def prever(self, x: pd.DataFrame) -> np.ndarray:
                return np.full(len(x), media)

        return _Constante()


def test_treino_nunca_recebe_alvo_nan_mesmo_com_lacuna() -> None:
    espiao = _EspiaoTreinador()
    TreinarEAvaliar(LeitorEmMemoria(_largo()), espiao).executar(SENSOR, INICIO, FIM_TREINO, CONFIG)
    assert espiao.vistos
    assert all(not y.isna().any() for _, y in espiao.vistos)
    assert all(list(x.columns) == list(FEATURES) for x, _ in espiao.vistos)


def test_alertas_trazem_explicacao_e_status_de_candidato(resultado: ResultadoM3) -> None:
    alertas = resultado.deteccao.alertas
    for a in alertas:
        if a.tipo == TIPO_ZSCORE:
            assert a.top_shap is None
            assert a.janela_inicio == INICIO and a.janela_fim == FIM_TREINO
            assert abs(a.z) >= 4.0
        else:
            assert a.tipo == TIPO_LIGHTGBM
            assert a.top_shap is not None and len(a.top_shap) == 3
    assert resultado.deteccao.d7_agregado is not None
    assert sum(resultado.deteccao.d7_agregado.participacao_por_feature.values()) == pytest.approx(1.0)


def test_benchmark_sintetico_com_semente_fixa(resultado: ResultadoM3) -> None:
    b = resultado.benchmark
    assert b.sintetico and b.semente == 11
    for nome in (TIPO_ZSCORE, TIPO_LIGHTGBM):
        t = b.taxas[nome]
        assert sum(t.injetados.values()) == 2 * 3 * 2  # 2 equipamentos x 3 tipos x 2 eventos
        assert t.taxa_deteccao("pico") == 1.0
        assert t.taxa_deteccao() >= 0.8
        assert t.taxa_falso_alarme() < 0.02


def test_benchmark_e_reprodutivel() -> None:
    a = _executar(_largo()).benchmark
    b = _executar(_largo()).benchmark
    assert {k: v.detectados for k, v in a.taxas.items()} == {k: v.detectados for k, v in b.taxas.items()}


def test_antes_depois_recupera_reducao_sintetica_dentro_da_tolerancia(resultado: ResultadoM3) -> None:
    ad = resultado.antes_depois
    assert ad.reducao is not None and ad.reducao.equipamento == "ac"
    assert ad.dentro_da_tolerancia
    assert ad.recuperado_pct == pytest.approx(15.0, abs=ad.tolerancia_pp)
    assert abs(resultado.controle.por_equipamento["ac"].economia_pct) < 3.0
    assert all(abs(v - 15.0) <= 3.0 for v in resultado.varredura_recuperado_pct.values())
    assert not ad.por_equipamento["ac"].baseline_fraca


def test_baseline_com_pouco_historico_sai_marcada_como_fraca() -> None:
    largo = _largo()
    cfg = ConfigAvaliacao(treino_inicial=pd.Timedelta(weeks=1), teste=pd.Timedelta(weeks=1))
    fim = INICIO + pd.Timedelta(weeks=3)
    res = TreinarEAvaliar(LeitorEmMemoria(largo), TreinadorLightGBM(n_arvores=20)).executar(SENSOR, INICIO, fim, cfg)
    assert all(m.baseline.fraca for m in res.modelos.values())
    assert all(m.baseline.semanas_completas == 3 for m in res.modelos.values())


def test_comparacao_com_controle_e_consistente_com_a_selecao(resultado: ResultadoM3) -> None:
    """Cada equipamento tem resultado do novo metodo; sem controle valido e NaN, com controle nunca inclui o tratado."""
    ad = resultado.antes_depois
    assert set(ad.por_equipamento_controle) == set(ad.por_equipamento)
    for eq, c in ad.por_equipamento_controle.items():
        assert eq not in c.controles
        assert (len(c.controles) == 0) == (c.motivo_invalido is not None)
        assert np.isnan(c.economia_pct) == (c.motivo_invalido is not None)
    assert resultado.varredura.controles.keys() == resultado.varredura.controle_pct.keys()
