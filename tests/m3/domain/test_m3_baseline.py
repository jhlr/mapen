from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.baseline import ajustar_baseline, contar_semanas_completas, esperado_em, zscore
from mapen_modelos.domain.features import tipo_dia

SEG = pd.Timestamp("2026-10-05")


def _padrao_semanal(semanas: int, ruido: float = 0.0, semente: int = 0) -> pd.Series:
    idx = pd.date_range(SEG, periods=168 * semanas, freq="1h")
    base = np.where(idx.hour.to_numpy() >= 8, 5.0, 1.0) + tipo_dia(idx) * 0.1
    rng = np.random.default_rng(semente)
    return pd.Series(base + rng.normal(0.0, ruido, len(idx)), index=idx)


def test_esperado_igual_ao_padrao_em_serie_sem_ruido() -> None:
    serie = _padrao_semanal(6)
    b = ajustar_baseline(serie)
    futuro = pd.date_range(SEG + pd.Timedelta(weeks=6), periods=168, freq="1h")
    esperado = np.where(futuro.hour.to_numpy() >= 8, 5.0, 1.0) + tipo_dia(futuro) * 0.1
    assert np.allclose(esperado_em(b, futuro), esperado)


def test_zscore_de_anomalia_injetada_e_alto_e_o_resto_e_baixo() -> None:
    treino = _padrao_semanal(8, ruido=0.2, semente=1)
    b = ajustar_baseline(treino)
    teste = _padrao_semanal(1, ruido=0.2, semente=2)
    teste.index = teste.index + pd.Timedelta(weeks=8)
    teste.iloc[30] += 5.0
    z = zscore(b, teste)
    assert z.iloc[30] > 8
    assert z.drop(z.index[30]).abs().max() < 4.5


def test_baseline_fraca_com_menos_de_quatro_semanas_completas() -> None:
    assert ajustar_baseline(_padrao_semanal(3)).fraca
    assert not ajustar_baseline(_padrao_semanal(4)).fraca
    assert ajustar_baseline(_padrao_semanal(3)).semanas_completas == 3


def test_semana_com_pouca_cobertura_nao_conta_como_completa() -> None:
    serie = _padrao_semanal(4)
    serie.iloc[168 : 168 + 100] = np.nan  # semana 2 com 40% de horas validas
    assert contar_semanas_completas(serie) == 3
    assert ajustar_baseline(serie).fraca


def test_feriado_usa_o_padrao_de_domingo() -> None:
    # 10 semanas a partir de segunda 2026-06-01; 2026-06-04 (quinta) e Corpus Christi.
    ini = pd.Timestamp("2026-06-01")
    idx = pd.date_range(ini, periods=168 * 10, freq="1h")
    dia = np.where(idx.dayofweek.to_numpy() == 6, 0.5, 4.0)
    serie = pd.Series(dia, index=idx)
    feriados = idx.normalize() == pd.Timestamp("2026-06-04")
    serie[feriados] = 0.5  # o equipamento se comporta como domingo no feriado
    b = ajustar_baseline(serie)
    assert np.allclose(b.esperado[3 * 24 : 4 * 24], 4.0, atol=0.3)  # quinta tem 9 quintas normais e 1 feriado
    assert np.allclose(b.esperado[6 * 24 : 7 * 24], 0.5, atol=1e-9)
    assert (serie[feriados] == esperado_em(b, pd.DatetimeIndex(serie[feriados].index))).all()


def test_treino_vazio_ou_sem_valores_falha() -> None:
    with pytest.raises(ValueError):
        ajustar_baseline(pd.Series([], index=pd.DatetimeIndex([]), dtype=float))
    idx = pd.date_range(SEG, periods=24, freq="1h")
    with pytest.raises(ValueError):
        ajustar_baseline(pd.Series(np.nan, index=idx))


def test_desvio_tem_piso_para_serie_constante() -> None:
    idx = pd.date_range(SEG, periods=168 * 5, freq="1h")
    b = ajustar_baseline(pd.Series(2.0, index=idx))
    assert (b.desvio > 0).all()
    z = zscore(b, pd.Series([2.0], index=idx[:1]))
    assert z.iloc[0] == 0.0
