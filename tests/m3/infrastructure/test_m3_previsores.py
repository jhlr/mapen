from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.application.portas import Previsor
from mapen_modelos.domain.features import tipo_dia
from mapen_modelos.domain.previsao import FEATURES_PREVISAO
from mapen_modelos.infrastructure.previsor_ets import PrevisorETS
from mapen_modelos.infrastructure.previsor_lightgbm import PrevisorLightGBM
from mapen_modelos.infrastructure.previsor_ridge import PrevisorRidge
from mapen_modelos.infrastructure.previsores_simples import PrevisorBaselineSazonal, PrevisorNaiveSazonal

T0 = pd.Timestamp("2026-10-05 00:00")  # segunda-feira
SEMANAS = 10
TREINO_FIM = T0 + pd.Timedelta(weeks=8)  # segunda-feira, 2026-11-30 (sem feriado nacional na semana seguinte)


def _perfil(indice: pd.DatetimeIndex) -> np.ndarray:
    """Estrutura conhecida: dia util 5 kW das 8h as 18h, sabado 3 kW das 8h as 14h, resto 1 kW."""
    hora = indice.hour.to_numpy()
    tipo = tipo_dia(indice)
    util = np.where((hora >= 8) & (hora < 18), 5.0, 1.0)
    sabado = np.where((hora >= 8) & (hora < 14), 3.0, 1.0)
    return np.asarray(np.where(tipo <= 4, util, np.where(tipo == 5, sabado, 1.0)), dtype=np.float64)


def _serie(ruido: float = 0.05) -> pd.Series:
    idx = pd.date_range(T0, periods=SEMANAS * 168, freq="1h")
    rng = np.random.default_rng(3)
    return pd.Series(_perfil(idx) + rng.normal(0, ruido, len(idx)), index=idx)


def _sem(serie: pd.Series, *instantes: pd.Timestamp) -> pd.Series:
    """Copia de `serie` com os instantes dados ausentes (NaN)."""
    return serie.mask(serie.index.isin(list(instantes)))


def _alvo(dias: int = 7) -> pd.DatetimeIndex:
    return pd.date_range(TREINO_FIM, periods=24 * dias, freq="1h")


def _mae(previsor: Previsor, serie: pd.Series, alvo: pd.DatetimeIndex) -> float:
    previsto = previsor.prever(serie, TREINO_FIM, alvo)
    assert list(previsto.index) == list(alvo)
    assert not previsto.isna().any()
    return float(np.abs(previsto.to_numpy() - _perfil(alvo)).mean())


def test_naive_168_acerta_estrutura_semanal_e_naive_24_erra_na_virada_de_tipo_de_dia() -> None:
    serie, alvo = _serie(), _alvo()
    mae168 = _mae(PrevisorNaiveSazonal(168), serie, alvo)
    mae24 = _mae(PrevisorNaiveSazonal(24), serie, alvo)
    assert mae168 < 0.1
    assert mae24 > 3 * mae168  # sab, dom e seg herdam o dia errado
    assert PrevisorNaiveSazonal(168).nome == "seasonal_naive_168"


def test_baseline_sazonal_recupera_a_media_por_hora_da_semana() -> None:
    assert _mae(PrevisorBaselineSazonal(), _serie(), _alvo()) < 0.05


def test_ridge_aprende_o_perfil_semanal_com_calendario_e_lags() -> None:
    assert _mae(PrevisorRidge(), _serie(), _alvo()) < 0.15


def test_ets_24_por_tipo_de_dia_aprende_o_perfil_semanal() -> None:
    assert _mae(PrevisorETS(), _serie(), _alvo()) < 0.15


def test_lightgbm_com_lag24_aprende_o_perfil_semanal() -> None:
    assert _mae(PrevisorLightGBM(n_arvores=80), _serie(), _alvo()) < 0.2


@pytest.mark.parametrize(
    "previsor",
    [
        PrevisorNaiveSazonal(24),
        PrevisorNaiveSazonal(168),
        PrevisorBaselineSazonal(),
        PrevisorRidge(),
        PrevisorETS(),
        PrevisorLightGBM(n_arvores=30),
    ],
    ids=lambda p: p.nome,
)
def test_previsao_do_dia_nao_enxerga_dados_a_partir_da_meia_noite(previsor: Previsor) -> None:
    """Adultera todo valor a partir da meia-noite do dia alvo: a previsao do dia nao pode mudar."""
    serie = _serie()
    alvo = _alvo(1)
    limpa = previsor.prever(serie, TREINO_FIM, alvo)
    adulterada = serie.copy()
    adulterada[adulterada.index >= TREINO_FIM] = 999.0
    depois = previsor.prever(adulterada, TREINO_FIM, alvo)
    assert np.array_equal(limpa.to_numpy(), depois.to_numpy(), equal_nan=True)


def test_modelos_com_features_usam_exatamente_a_lista_permitida() -> None:
    """Guard de ligacao: o que Ridge e LightGBM consomem e a lista que o guard de defasagem valida."""
    assert PrevisorRidge.features == FEATURES_PREVISAO
    assert PrevisorLightGBM.features == FEATURES_PREVISAO
    assert not any(f.endswith("lag1") for f in FEATURES_PREVISAO)


def test_ridge_nao_imputa_lacunas_so_deixa_nan_onde_a_feature_falta() -> None:
    """Hora ausente no dia anterior: NaN apenas nas horas alvo cujo lag 24 e essa hora."""
    ausente = TREINO_FIM - pd.Timedelta(hours=10)  # 14:00 do domingo anterior
    serie = _sem(_serie(), ausente)
    alvo = _alvo(2)
    previsto = PrevisorRidge().prever(serie, TREINO_FIM, alvo)
    nan = previsto[previsto.isna()].index
    assert list(nan) == [ausente + pd.Timedelta(hours=24), ausente + pd.Timedelta(hours=48)]


def test_lightgbm_preve_mesmo_com_lag_ausente_sem_interpolar() -> None:
    serie = _sem(_serie(), TREINO_FIM - pd.Timedelta(hours=10))
    previsto = PrevisorLightGBM(n_arvores=30).prever(serie, TREINO_FIM, _alvo(1))
    assert not previsto.isna().any()


def test_ets_dia_com_lacuna_equivale_a_dia_ausente() -> None:
    """Dia com uma hora faltando e descartado: o resultado e identico ao do dia inteiro ausente."""
    base = _serie()
    dia = pd.Timestamp("2026-11-10")  # terca-feira util
    com_lacuna = _sem(base, dia + pd.Timedelta(hours=5))
    sem_dia = base.copy()
    sem_dia[(sem_dia.index >= dia) & (sem_dia.index < dia + pd.Timedelta(days=1))] = np.nan
    alvo = _alvo(1)
    a = PrevisorETS().prever(com_lacuna, TREINO_FIM, alvo)
    b = PrevisorETS().prever(sem_dia, TREINO_FIM, alvo)
    assert not a.isna().any()
    assert np.array_equal(a.to_numpy(), b.to_numpy())
    assert len(PrevisorETS._dias_completos(com_lacuna)) == len(PrevisorETS._dias_completos(base)) - 1


def test_ets_serie_constante_nao_quebra_e_repete_o_ultimo_dia_do_tipo() -> None:
    idx = pd.date_range(T0, periods=SEMANAS * 168, freq="1h")
    constante = pd.Series(2.0, index=idx)
    previsto = PrevisorETS().prever(constante, TREINO_FIM, _alvo(1))
    assert np.allclose(previsto.to_numpy(), 2.0)


def test_ets_sem_historico_suficiente_devolve_nan() -> None:
    idx = pd.date_range(T0, periods=3 * 24, freq="1h")
    previsto = PrevisorETS().prever(pd.Series(1.0, index=idx), T0 + pd.Timedelta(days=3), pd.date_range(T0 + pd.Timedelta(days=3), periods=24, freq="1h"))
    assert previsto.isna().all()


def test_contribuicoes_do_lightgbm_tem_as_colunas_das_features() -> None:
    serie = _serie()
    alvo = _alvo(1)
    previsor = PrevisorLightGBM(n_arvores=30)
    contrib = previsor.contribuicoes(serie, TREINO_FIM, alvo)
    assert list(contrib.columns) == list(FEATURES_PREVISAO) and len(contrib) == 24
    assert np.isfinite(contrib.to_numpy()).all()
