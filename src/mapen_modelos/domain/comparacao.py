"""Antes x depois com baseline normalizado.

O esperado vem de um baseline ajustado ANTES do periodo "antes" (hora da semana e feriado ja
normalizam o calendario). A deriva de nivel entre treino e o periodo "antes" e absorvida por
um fator `sum(obs_antes) / sum(esp_antes)`. O contrafactual do "depois" e esperado_depois x
fator; economia = contrafactual - observado, so nas horas com observado e esperado validos.
Temperatura nao entra (limite documentado).

Segundo metodo, com grupo-controle (diferenca em diferencas multiplicativa): a razao
depois/antes do equipamento tratado e dividida pela mesma razao de equipamentos de controle sem
intervencao, que absorvem a deriva de carga compartilhada (ocupacao, calendario). Os controles
sao escolhidos por regra fixa e testavel (`selecionar_controles`): maior correlacao do perfil
semanal pre-periodo, excluindo o proprio tratado.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ResultadoComparacao:
    kwh_antes: float
    kwh_depois: float
    fator_nivel: float
    kwh_contrafactual: float
    economia_kwh: float
    economia_pct: float
    horas_antes: int
    horas_depois: int
    baseline_fraca: bool


def comparar_antes_depois(
    observado_antes: pd.Series,
    esperado_antes: pd.Series,
    observado_depois: pd.Series,
    esperado_depois: pd.Series,
    baseline_fraca: bool,
) -> ResultadoComparacao:
    """Economia normalizada. As series devem estar alinhadas (mesmo indice) em cada periodo."""
    if not observado_antes.index.equals(esperado_antes.index):
        raise ValueError("antes: observado e esperado precisam do mesmo indice")
    if not observado_depois.index.equals(esperado_depois.index):
        raise ValueError("depois: observado e esperado precisam do mesmo indice")
    ok_a = observado_antes.notna() & esperado_antes.notna()
    ok_d = observado_depois.notna() & esperado_depois.notna()
    obs_a = float(observado_antes[ok_a].sum())
    esp_a = float(esperado_antes[ok_a].sum())
    obs_d = float(observado_depois[ok_d].sum())
    esp_d = float(esperado_depois[ok_d].sum())
    if esp_a <= 0.0 or esp_d <= 0.0:
        return ResultadoComparacao(
            obs_a, obs_d, float("nan"), float("nan"), float("nan"), float("nan"),
            int(ok_a.sum()), int(ok_d.sum()), baseline_fraca,
        )
    fator = obs_a / esp_a
    contrafactual = esp_d * fator
    economia = contrafactual - obs_d
    pct = float(100.0 * economia / contrafactual) if contrafactual > 0 else float("nan")
    return ResultadoComparacao(
        kwh_antes=obs_a,
        kwh_depois=obs_d,
        fator_nivel=fator,
        kwh_contrafactual=contrafactual,
        economia_kwh=economia,
        economia_pct=pct,
        horas_antes=int(ok_a.sum()),
        horas_depois=int(ok_d.sum()),
        baseline_fraca=baseline_fraca,
    )


def aplicar_reducao(serie: pd.Series, a_partir_de: pd.Timestamp, fracao: float) -> pd.Series:
    """Reducao sintetica: multiplica por (1 - fracao) de `a_partir_de` em diante."""
    if not 0.0 <= fracao < 1.0:
        raise ValueError("fracao deve estar em [0, 1)")
    fator = np.where(pd.DatetimeIndex(serie.index) >= a_partir_de, 1.0 - fracao, 1.0)
    return serie * fator


# ------------------------------------------------------------------ grupo-controle

NOME_METODO_BASELINE = "baseline_normalizado"
NOME_METODO_CONTROLE = "diferenca_em_diferencas_grupo_controle"
N_CONTROLES_PADRAO = 3
CORRELACAO_MINIMA_PADRAO = 0.5
DESCRICAO_REGRA_CONTROLES = (
    f"ate {N_CONTROLES_PADRAO} equipamentos do mesmo andar com maior correlacao do perfil semanal pre-periodo "
    f"(minimo {CORRELACAO_MINIMA_PADRAO}), sem o tratado"
)
HORAS_POR_SEMANA = 168
COBERTURA_SEMANA_MINIMA = 0.9


def perfil_semanal(serie: pd.Series) -> pd.Series:
    """Media horaria por semana (blocos de 168 h a partir do primeiro indice); semana com menos de 90% de horas validas vira NaN."""
    if len(serie) == 0:
        return pd.Series(dtype=float)
    bloco = ((pd.DatetimeIndex(serie.index) - serie.index[0]) // pd.Timedelta(hours=HORAS_POR_SEMANA)).to_numpy()
    grupos = serie.groupby(bloco)
    media = grupos.mean()
    validas = grupos.count()
    minimo = COBERTURA_SEMANA_MINIMA * HORAS_POR_SEMANA
    return media.where(validas.to_numpy() >= minimo)


def correlacao_perfil(a: pd.Series, b: pd.Series) -> float:
    """Pearson entre os perfis semanais (so semanas validas nos dois); NaN se faltar variancia ou menos de 4 semanas."""
    pa, pb = perfil_semanal(a), perfil_semanal(b)
    df = pd.concat([pa, pb], axis=1, join="inner").dropna()
    if len(df) < 4 or df.iloc[:, 0].std() == 0.0 or df.iloc[:, 1].std() == 0.0:
        return float("nan")
    return float(np.corrcoef(df.iloc[:, 0], df.iloc[:, 1])[0, 1])


def selecionar_controles(
    alvo: str,
    series_pre: Mapping[str, pd.Series],
    n_controles: int = N_CONTROLES_PADRAO,
    correlacao_minima: float = CORRELACAO_MINIMA_PADRAO,
) -> tuple[str, ...]:
    """Regra: candidatos = todos menos o alvo; mantem corr(perfil semanal pre) >= minima; as `n_controles` maiores.

    Desempate por nome (determinismo). Vazio quando nenhum candidato passa: nao ha controle valido.
    """
    if n_controles < 1:
        raise ValueError("n_controles deve ser >= 1")
    if alvo not in series_pre:
        raise ValueError("alvo ausente das series")
    pontuados = [
        (correlacao_perfil(series_pre[alvo], s), eq) for eq, s in series_pre.items() if eq != alvo
    ]
    validos = [(c, eq) for c, eq in pontuados if not np.isnan(c) and c >= correlacao_minima]
    validos.sort(key=lambda t: (-t[0], t[1]))
    return tuple(eq for _, eq in validos[:n_controles])


@dataclass(frozen=True)
class ResultadoComparacaoControle:
    metodo: str
    controles: tuple[str, ...]
    kwh_antes: float
    kwh_depois: float
    razao_tratado: float
    razao_controle: float
    kwh_contrafactual: float
    economia_kwh: float
    economia_pct: float
    baseline_fraca: bool
    motivo_invalido: str | None


def _sem_controle(
    controles: tuple[str, ...], kwh_a: float, kwh_d: float, fraca: bool, motivo: str
) -> ResultadoComparacaoControle:
    nan = float("nan")
    return ResultadoComparacaoControle(
        NOME_METODO_CONTROLE, controles, kwh_a, kwh_d, nan, nan, nan, nan, nan, fraca, motivo
    )


def comparar_com_controle(
    tratado_antes: pd.Series,
    tratado_depois: pd.Series,
    controles_antes: Mapping[str, pd.Series],
    controles_depois: Mapping[str, pd.Series],
    baseline_fraca: bool,
) -> ResultadoComparacaoControle:
    """Economia = 1 - (kWh depois / kWh antes do tratado) / (idem do controle), usando so horas validas em todas as series.

    Os controles sao somados (razao de kWh agregado). Sem controle, ou com consumo antes <= 0, o resultado e NaN com `motivo_invalido`.
    """
    nomes = tuple(controles_antes)
    if set(nomes) != set(controles_depois):
        raise ValueError("controles de antes e depois devem ser os mesmos")
    if not nomes:
        return _sem_controle((), float(tratado_antes.sum()), float(tratado_depois.sum()), baseline_fraca, "sem controle valido")
    antes = pd.concat([tratado_antes, *(controles_antes[n] for n in nomes)], axis=1, join="inner").dropna()
    depois = pd.concat([tratado_depois, *(controles_depois[n] for n in nomes)], axis=1, join="inner").dropna()
    t_a, t_d = float(antes.iloc[:, 0].sum()), float(depois.iloc[:, 0].sum())
    c_a, c_d = float(antes.iloc[:, 1:].sum().sum()), float(depois.iloc[:, 1:].sum().sum())
    if t_a <= 0.0 or c_a <= 0.0 or c_d <= 0.0:
        return _sem_controle(nomes, t_a, t_d, baseline_fraca, "consumo antes ou razao do controle nao positivo")
    razao_t, razao_c = t_d / t_a, c_d / c_a
    contrafactual = t_a * razao_c
    return ResultadoComparacaoControle(
        metodo=NOME_METODO_CONTROLE,
        controles=nomes,
        kwh_antes=t_a,
        kwh_depois=t_d,
        razao_tratado=razao_t,
        razao_controle=razao_c,
        kwh_contrafactual=contrafactual,
        economia_kwh=contrafactual - t_d,
        economia_pct=float(100.0 * (1.0 - razao_t / razao_c)),
        baseline_fraca=baseline_fraca,
        motivo_invalido=None,
    )


@dataclass(frozen=True)
class ResumoVarredura:
    """Erro (pp) de um metodo ao recuperar uma reducao conhecida, um equipamento tratado por vez."""

    avaliados: int
    dentro_da_tolerancia: int
    sem_resultado: tuple[str, ...]
    erro_abs_mediano_pp: float
    erro_abs_maximo_pp: float


def resumir_varredura(recuperado_pct: Mapping[str, float], alvo_pct: float, tolerancia_pp: float) -> ResumoVarredura:
    """Equipamento com recuperado NaN (sem controle valido) conta como fora da tolerancia e fica fora das medianas."""
    sem = tuple(eq for eq, v in recuperado_pct.items() if np.isnan(v))
    erros = np.array([abs(v - alvo_pct) for v in recuperado_pct.values() if not np.isnan(v)])
    return ResumoVarredura(
        avaliados=len(recuperado_pct),
        dentro_da_tolerancia=int((erros <= tolerancia_pp).sum()),
        sem_resultado=sem,
        erro_abs_mediano_pp=float(np.median(erros)) if len(erros) else float("nan"),
        erro_abs_maximo_pp=float(erros.max()) if len(erros) else float("nan"),
    )
