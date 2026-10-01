from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mapen_modelos.application.estudo_previsao import EstudoPrevisao, ParametrosPrevisao
from mapen_modelos.application.portas import Previsor
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao
from mapen_modelos.domain.features import tipo_dia
from mapen_modelos.domain.metricas_previsao import NAIVE_168
from mapen_modelos.domain.previsao import FEATURES_PREVISAO
from mapen_modelos.infrastructure.previsor_ets import PrevisorETS
from mapen_modelos.infrastructure.previsor_lightgbm import PrevisorLightGBM
from mapen_modelos.infrastructure.previsor_ridge import PrevisorRidge
from mapen_modelos.infrastructure.previsores_simples import PrevisorBaselineSazonal, PrevisorNaiveSazonal
from mapen_modelos.interface.artefatos_previsao import montar_previsao_json, renderizar_relatorio
from mapen_modelos.interface.artefatos_json import serializar

T0 = pd.Timestamp("2026-10-05 00:00")  # segunda-feira
ORDEM = ("seasonal_naive_24", NAIVE_168, "baseline_sazonal", "ridge", "ets_24_tipo_dia", "lightgbm_lag24")


class LeitorFalso:
    """Duas cargas com perfil semanal conhecido e um equipamento desligado."""

    def ler_series_horarias(self, sensor_id: str, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
        idx = pd.date_range(inicio, fim, freq="1h", inclusive="left")
        rng = np.random.default_rng(7)
        hora = idx.hour.to_numpy()
        util = np.where((hora >= 8) & (hora < 18), 5.0, 1.0)
        fim_de_semana = tipo_dia(idx) > 4
        return pd.DataFrame(
            {
                "carga_a": np.where(fim_de_semana, 1.0, util) + rng.normal(0, 0.05, len(idx)),
                "carga_b": 2.0 * np.where(fim_de_semana, 1.0, util) + rng.normal(0, 0.1, len(idx)),
                "desligado": 0.0,
            },
            index=idx,
        )


def _previsores(lgbm: PrevisorLightGBM) -> list[Previsor]:
    return [
        PrevisorNaiveSazonal(24),
        PrevisorNaiveSazonal(168),
        PrevisorBaselineSazonal(),
        PrevisorRidge(),
        PrevisorETS(),
        lgbm,
    ]


def _executar() -> EstudoPrevisao:
    return EstudoPrevisao(LeitorFalso(), _previsores(PrevisorLightGBM(n_arvores=30)), ORDEM, PrevisorLightGBM(n_arvores=30))


PARAMETROS = ParametrosPrevisao(
    "s", T0, T0 + pd.Timedelta(weeks=9), T0 + pd.Timedelta(weeks=11), limiar_z=4.0, semente=1, eventos_por_tipo=1
)
CONFIG = ConfigAvaliacao(treino_inicial=pd.Timedelta(weeks=5), teste=pd.Timedelta(weeks=2))


def test_estudo_compara_modelos_aplica_a_regra_e_roda_o_benchmark_sintetico() -> None:
    r = _executar().executar(PARAMETROS, CONFIG)
    assert r.equipamentos == ["carga_a", "carga_b"] and r.sem_carga == ["desligado"]
    assert len(r.dobras) == 2 and r.modelos == list(ORDEM)
    mase = r.mase_reservado()
    # estrutura conhecida: o naive de 24 h erra na virada util -> fim de semana; os demais acertam o perfil
    assert mase["seasonal_naive_24"]["carga_a"] > 3 * mase[NAIVE_168]["carga_a"]
    assert mase["baseline_sazonal"]["carga_a"] < 1.0 and mase["ridge"]["carga_a"] < 1.5
    assert r.decisao.adotado in r.modelos
    assert all(m.horas > 300 for por_eq in r.reservado.values() for m in por_eq.values())
    assert r.shap is not None and sum(r.shap.participacao_por_grupo.values()) == pytest.approx(1.0)
    assert r.benchmark is not None and r.benchmark.sintetico
    assert sum(r.benchmark.taxas.injetados.values()) == 6  # 3 tipos x 1 evento x 2 equipamentos
    assert r.benchmark.taxas.taxa_deteccao("pico") == 1.0
    assert set(r.shap.participacao_por_feature) == set(FEATURES_PREVISAO)


def test_artefatos_serializam_sem_nan_e_trazem_a_decisao() -> None:
    r = _executar().executar(PARAMETROS, CONFIG)
    texto = serializar(montar_previsao_json(r))  # allow_nan=False: falha se sobrar NaN
    assert '"natureza": "estudo_previsao_dia_seguinte"' in texto and f'"adotado": "{r.decisao.adotado}"' in texto
    assert "Decisao:" in renderizar_relatorio(r)


def test_ordem_de_simplicidade_precisa_listar_os_previsores_e_a_referencia() -> None:
    with pytest.raises(ValueError):
        EstudoPrevisao(LeitorFalso(), [PrevisorNaiveSazonal(24), PrevisorNaiveSazonal(168)], ("seasonal_naive_24",))
    with pytest.raises(ValueError):
        EstudoPrevisao(LeitorFalso(), [PrevisorNaiveSazonal(24)], ("seasonal_naive_24",))
