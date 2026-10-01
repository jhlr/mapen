from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.domain.metricas_previsao import (
    NAIVE_168,
    decidir_adocao,
    escala_mase,
    metricas,
    participacao_por_grupo,
    suporte_comum,
)
from mapen_modelos.domain.previsao import (
    FEATURES_PREVISAO,
    ConstrutorFeatures,
    defasagem_violadora,
    montar_features_previsao,
    naive_sazonal,
)

T0 = pd.Timestamp("2026-10-05 00:00")  # segunda-feira


def _serie_aleatoria(horas: int = 400) -> pd.Series:
    rng = np.random.default_rng(1)
    return pd.Series(rng.uniform(1.0, 5.0, horas), index=pd.date_range(T0, periods=horas, freq="1h"))


def construtor_violador(serie: pd.Series, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    """Feature deliberadamente violadora: `kw_lag1` (defasagem 1 h)."""
    quadro = montar_features_previsao(serie, inicio, fim)
    quadro["kw_lag1"] = quadro["kw"].shift(1)
    return quadro


def construtor_janela_sem_deslocamento(serie: pd.Series, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    """Janela movel de 24 h que termina em t-1 (esquecendo o deslocamento de 24 h)."""
    quadro = montar_features_previsao(serie, inicio, fim)
    quadro["kw_media24_d24"] = quadro["kw"].shift(1).rolling(24, min_periods=12).mean()
    return quadro


# Construtor sob guarda. A prova vermelha troca esta linha por `construtor_violador`.
CONSTRUTOR: ConstrutorFeatures = montar_features_previsao


def test_nenhuma_feature_de_previsao_usa_defasagem_menor_que_24h() -> None:
    """Guard da regra de defasagem: perturba cada hora dos 24 h anteriores e exige features inalteradas."""
    assert defasagem_violadora(CONSTRUTOR, _serie_aleatoria()) == []


def test_guard_detecta_lag1() -> None:
    assert defasagem_violadora(construtor_violador, _serie_aleatoria()) == ["kw_lag1"]


def test_guard_detecta_janela_movel_sem_deslocamento() -> None:
    assert defasagem_violadora(construtor_janela_sem_deslocamento, _serie_aleatoria()) == ["kw_media24_d24"]


def test_guard_aceita_a_defasagem_exata_de_24h() -> None:
    """kw_lag24 depende do valor de 24 h antes: permitido; a lista de features cobre calendario, lags e janela."""
    quadro = montar_features_previsao(_serie_aleatoria(), T0, T0 + pd.Timedelta(hours=400))
    assert list(quadro.columns) == ["kw", *FEATURES_PREVISAO]
    assert "kw_lag1" not in quadro.columns
    t = T0 + pd.Timedelta(hours=200)
    assert quadro.loc[t, "kw_lag24"] == quadro.loc[t - pd.Timedelta(hours=24), "kw"]


def test_janela_movel_termina_na_defasagem_24() -> None:
    serie = pd.Series(np.arange(300, dtype=float), index=pd.date_range(T0, periods=300, freq="1h"))
    q = montar_features_previsao(serie, T0, T0 + pd.Timedelta(hours=300))
    t = T0 + pd.Timedelta(hours=100)
    assert q.loc[t, "kw_media24_d24"] == np.mean(np.arange(53, 77))  # horas 53..76 = [t-47, t-24]


def test_lacuna_nao_e_interpolada_nas_features_de_previsao() -> None:
    """Hora 100 ausente: lag24 em 124 e NaN; a janela tolera lacuna curta (media das validas) e falha em lacuna longa."""
    horas = [h for h in range(400) if h != 100]
    serie = pd.Series([float(h) for h in horas], index=pd.DatetimeIndex([T0 + pd.Timedelta(hours=h) for h in horas]))
    q = montar_features_previsao(serie, T0, T0 + pd.Timedelta(hours=400))
    assert pd.isna(q.loc[T0 + pd.Timedelta(hours=100), "kw"])
    assert pd.isna(q.loc[T0 + pd.Timedelta(hours=124), "kw_lag24"])
    assert q.loc[T0 + pd.Timedelta(hours=125), "kw_lag24"] == 101.0
    t = T0 + pd.Timedelta(hours=130)  # janela [83, 106] contem a hora 100
    assert q.loc[t, "kw_media24_d24"] == pytest.approx(np.mean([h for h in range(83, 107) if h != 100]))
    longa = serie.drop([T0 + pd.Timedelta(hours=h) for h in range(101, 114)])  # 100..113: 14 horas ausentes
    q2 = montar_features_previsao(longa, T0, T0 + pd.Timedelta(hours=400))
    assert pd.isna(q2.loc[T0 + pd.Timedelta(hours=140), "kw_media24_d24"])  # janela [93, 116]: 10 validas < 12


def test_hora_da_semana_trata_feriado_como_domingo() -> None:
    idx = pd.date_range("2026-09-07", periods=24, freq="1h")  # 7 de setembro: feriado numa segunda
    serie = pd.Series(1.0, index=idx)
    q = montar_features_previsao(serie, idx[0], idx[-1] + pd.Timedelta("1h"))
    assert q["hora_semana"].iloc[0] == 6 * 24 and q["feriado"].iloc[0] == 1


def test_naive_sazonal_olha_o_valor_de_p_horas_antes_e_recusa_periodo_curto() -> None:
    serie = pd.Series(np.arange(300, dtype=float), index=pd.date_range(T0, periods=300, freq="1h"))
    alvo = pd.date_range(T0 + pd.Timedelta(hours=200), periods=3, freq="1h")
    assert naive_sazonal(serie, 168, alvo).tolist() == [32.0, 33.0, 34.0]
    assert np.isnan(naive_sazonal(serie, 168, pd.DatetimeIndex([T0 + pd.Timedelta(hours=100)]))[0])
    with pytest.raises(ValueError):
        naive_sazonal(serie, 1, alvo)


def test_escala_mase_e_mase_conhecidos() -> None:
    idx = pd.date_range(T0, periods=336, freq="1h")
    treino = pd.Series(np.where(np.arange(336) < 168, 1.0, 3.0), index=idx)  # semana 2 = semana 1 + 2
    assert escala_mase(treino) == pytest.approx(2.0)
    m = metricas(np.array([1.0, 3.0]), np.array([2.0, 5.0]), 2.0)
    assert (m.mae, m.horas) == (1.5, 2) and m.mase == pytest.approx(0.75) and m.rmse == pytest.approx(np.sqrt(2.5))


def test_suporte_comum_exige_alvo_e_todas_as_previsoes() -> None:
    y = np.array([1.0, np.nan, 3.0, 4.0])
    ok = suporte_comum(y, {"a": np.array([1.0, 1.0, np.nan, 1.0]), "b": np.ones(4)})
    assert ok.tolist() == [True, False, False, True]


ORDEM = ("seasonal_naive_24", NAIVE_168, "baseline_sazonal", "ridge", "ets", "lgbm")


def _mase(**medianas: float) -> dict[str, dict[str, float]]:
    """MASE constante por equipamento (20 equipamentos), um valor por modelo."""
    return {m: {f"e{i}": medianas.get(m, 1.0) for i in range(20)} for m in ORDEM}


def test_decisao_adota_o_mais_simples_dentro_de_5pct_dos_que_passaram() -> None:
    mase = _mase(seasonal_naive_24=1.3, ridge=0.80, ets=0.79, lgbm=0.60)
    d = decidir_adocao(mase, ORDEM)
    assert d.passaram == ["ridge", "ets", "lgbm"] and d.regra_aplicada == "ganho_e_vitorias"
    assert d.adotado == "lgbm"  # 0.60 e o melhor e ninguem mais simples esta dentro de 5%


def test_decisao_sem_ganho_de_10pct_cai_na_regra_do_mais_simples() -> None:
    mase = _mase(seasonal_naive_24=1.3, baseline_sazonal=0.97, ridge=0.95, ets=0.93, lgbm=0.92)
    d = decidir_adocao(mase, ORDEM)
    assert d.passaram == [] and d.regra_aplicada == "mais_simples_dentro_de_5pct"
    assert d.adotado == "ridge"  # limite 1.05 x 0.92 = 0.966: naive-168 (1.0) e baseline (0.97) ficam de fora
    assert d.melhor_mediana == "lgbm"


def test_decisao_exige_12_vitorias_alem_da_mediana() -> None:
    mase = _mase(ridge=0.5)
    for i in range(9):  # perde para o naive em 9 equipamentos: sobram 11 vitorias
        mase["ridge"][f"e{i}"] = 1.5
    d = decidir_adocao(mase, ORDEM)
    assert d.vitorias_vs_naive168["ridge"] == 11 and d.passaram == []


def test_participacao_por_grupo_soma_as_features_do_grupo() -> None:
    g = participacao_por_grupo({"hora": 0.1, "kw_lag24": 0.5, "kw_lag168": 0.2, "kw_desvio24_d24": 0.2})
    assert g == {"calendario": pytest.approx(0.1), "lags": pytest.approx(0.7), "janela_movel": pytest.approx(0.2)}
