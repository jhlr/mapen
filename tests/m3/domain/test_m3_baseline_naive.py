from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.baseline_naive import zscore_naive168

SEG = pd.Timestamp("2026-10-05")  # segunda-feira
SEMANA = pd.Timedelta(weeks=1)


def _serie(semanas: int, ruido: float = 0.2, semente: int = 0) -> pd.Series:
    idx = pd.date_range(SEG, periods=168 * semanas, freq="1h")
    base = np.where(idx.hour.to_numpy() >= 8, 5.0, 1.0)
    rng = np.random.default_rng(semente)
    return pd.Series(base + rng.normal(0.0, ruido, len(idx)), index=idx)


def _somar(serie: pd.Series, ts: pd.Timestamp, valor: float) -> None:
    serie.at[ts] = float(serie.loc[[ts]].iloc[0]) + valor


def _ts(semana: int, hora_da_semana: int = 0) -> pd.Timestamp:
    return SEG + semana * SEMANA + pd.Timedelta(hours=hora_da_semana)


def test_esperado_e_o_valor_de_168_horas_antes() -> None:
    serie = _serie(8)
    r = zscore_naive168(serie, _ts(6), _ts(8))
    alvo = pd.DatetimeIndex(r.indice)
    assert alvo[0] == _ts(6) and len(alvo) == 2 * 168
    assert np.array_equal(r.esperado, serie.reindex(alvo - SEMANA).to_numpy())


def test_pico_injetado_e_detectado_e_o_resto_fica_abaixo_do_limiar() -> None:
    serie = _serie(8)
    _somar(serie, _ts(6, 30), 5.0)
    r = zscore_naive168(serie, _ts(6), _ts(8))
    z = pd.Series(r.z, index=r.indice)
    assert z.loc[_ts(6, 30)] > 4.0
    # o residuo da semana seguinte carrega o pico de 168 h antes (efeito documentado do naive)
    assert z.loc[_ts(7, 30)] < -4.0
    resto = z.drop([_ts(6, 30), _ts(7, 30)])
    assert resto.abs().max() < 4.0


def test_lacuna_no_observado_ou_na_referencia_deixa_z_nan() -> None:
    serie = _serie(8)
    serie.at[_ts(6, 10)] = np.nan
    r = zscore_naive168(serie, _ts(6), _ts(8))
    z = pd.Series(r.z, index=r.indice)
    assert np.isnan(z.loc[_ts(6, 10)])  # sem observado
    assert np.isnan(z.loc[_ts(7, 10)])  # sem referencia (168 h antes)
    assert z.drop([_ts(6, 10), _ts(7, 10)]).notna().all()


def test_escala_da_semana_k_so_usa_residuos_anteriores_ao_inicio_da_semana() -> None:
    serie = _serie(9)
    base = zscore_naive168(serie, _ts(6), _ts(9))
    alterada = serie.copy()
    alterada.loc[_ts(7, 0) : _ts(9) - pd.Timedelta(hours=1)] += 50.0  # muda semanas 7 e 8
    r = zscore_naive168(alterada, _ts(6), _ts(9))
    primeira = slice(0, 168)  # semana 6: nada depois dela pode mexer na escala ou no z dela
    assert np.array_equal(r.sigma[primeira], base.sigma[primeira])
    assert np.array_equal(r.z[primeira], base.z[primeira])
    # dentro da semana 7 a escala e a mesma, mesmo que os valores da propria semana mudem
    segunda = slice(168, 2 * 168)
    mudada_so_na_7 = serie.copy()
    mudada_so_na_7.loc[_ts(7, 0) : _ts(8) - pd.Timedelta(hours=1)] += 50.0
    r7 = zscore_naive168(mudada_so_na_7, _ts(6), _ts(9))
    assert np.array_equal(r7.sigma[segunda], base.sigma[segunda])


def test_escala_e_refeita_a_cada_semana() -> None:
    serie = _serie(9, ruido=0.1)
    # a partir da semana 7 o ruido sobe: a escala da semana 8 tem de refletir isso
    ruido_alto = np.random.default_rng(5).normal(0.0, 1.5, 168 * 2)
    serie.loc[_ts(7, 0) : _ts(9) - pd.Timedelta(hours=1)] += ruido_alto
    r = zscore_naive168(serie, _ts(6), _ts(9), limiar=1e9)  # sem alertas: nada e censurado
    s6, s7, s8 = r.sigma[:168], r.sigma[168:336], r.sigma[336:]
    assert np.median(s7) == pytest.approx(np.median(s6), rel=0.05)  # semana 7 so viu ruido baixo (ate a 6)
    assert np.median(s8) > 1.3 * np.median(s7)  # semana 8 ja viu os residuos da 7


def test_hora_que_virou_alerta_nao_infla_a_escala_das_semanas_seguintes() -> None:
    serie = _serie(9)
    sem_evento = zscore_naive168(serie, _ts(6), _ts(9))
    com_evento = serie.copy()
    _somar(com_evento, _ts(6, 30), 30.0)  # alerta na semana 6; residuos de 6 e 7 ficam enormes
    r = zscore_naive168(com_evento, _ts(6), _ts(9))
    z = pd.Series(r.z, index=r.indice)
    assert abs(z.loc[_ts(6, 30)]) >= 4.0 and abs(z.loc[_ts(7, 30)]) >= 4.0
    # na semana 8 a escala da hora 30 segue na ordem de grandeza sem evento (sem censura iria a ~16 kW,
    # 40x maior): os dois residuos gigantes ficaram fora da amostra
    assert r.sigma[2 * 168 + 30] < 2.0 * sem_evento.sigma[2 * 168 + 30]


def test_janela_da_escala_e_marca_de_baseline_fraca() -> None:
    serie = _serie(8)
    r = zscore_naive168(serie, _ts(6), _ts(8))
    assert r.janela_inicio == SEG
    assert pd.Timestamp(r.janela_fim[0]) == _ts(6) and pd.Timestamp(r.janela_fim[168]) == _ts(7)
    assert not r.fraca.any()  # 5 semanas completas de residuo antes da semana 6
    pouca = zscore_naive168(_serie(4), _ts(2), _ts(4))
    assert pouca.fraca.all()  # so 1 semana completa de residuo antes da semana 2


def test_serie_que_comeca_depois_do_inicio_e_erro() -> None:
    with pytest.raises(ValueError, match="comecar antes"):
        zscore_naive168(_serie(4), SEG - SEMANA, _ts(4))
