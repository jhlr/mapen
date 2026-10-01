"""Injecao de anomalias sinteticas conhecidas (benchmark SINTETICO, nao ha rotulo real).

Tres tipos: `pico` (1 h), `elevacao_fora_de_horario` (6 h de madrugada com carga somada) e
`ligado_continuo` (12 h a partir das 20:00 presas no nivel P95 de treino). A escala vem do P95
de treino do equipamento, entao equipamentos sem carga nao entram.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PICO = "pico"
ELEVACAO = "elevacao_fora_de_horario"
LIGADO = "ligado_continuo"
TIPOS: tuple[str, ...] = (PICO, ELEVACAO, LIGADO)
FATOR_PICO = 3.0
FATOR_ELEVACAO = 0.5
HORAS_ELEVACAO = 6
HORAS_LIGADO = 12
HORA_INICIO_LIGADO = 20
CARGA_MINIMA_KW = 0.05


@dataclass(frozen=True)
class EventoInjetado:
    tipo: str
    inicio: pd.Timestamp
    fim: pd.Timestamp  # exclusivo


def equipamento_com_carga(treino: pd.Series) -> bool:
    """True quando a media de treino e de pelo menos `CARGA_MINIMA_KW`."""
    valido = treino.dropna()
    return bool(len(valido) > 0 and float(valido.mean()) >= CARGA_MINIMA_KW)


def _inicios_possiveis(
    indice: pd.DatetimeIndex, horas: int, hora_fixa: int | None
) -> list[int]:
    """Posicoes onde um evento de `horas` cabe; `hora_fixa` exige inicio nessa hora do dia."""
    n = len(indice)
    pos = [i for i in range(0, n - horas + 1)]
    if hora_fixa is not None:
        pos = [i for i in pos if indice[i].hour == hora_fixa]
    return pos


def injetar_anomalias(
    serie: pd.Series,
    p95_treino: float,
    rng: np.random.Generator,
    por_tipo: int,
) -> tuple[pd.Series, list[EventoInjetado]]:
    """Copia de `serie` com `por_tipo` eventos de cada tipo, sem sobreposicao entre eventos.

    A serie e horaria e completa. Eventos nao se sobrepoem nem encostam (1 h de folga).
    """
    indice = pd.DatetimeIndex(serie.index)
    valores = serie.to_numpy(dtype=np.float64).copy()
    ocupado = np.zeros(len(valores), dtype=bool)
    eventos: list[EventoInjetado] = []
    especificacao = (
        (PICO, 1, None),
        (ELEVACAO, HORAS_ELEVACAO, 0),
        (LIGADO, HORAS_LIGADO, HORA_INICIO_LIGADO),
    )
    for tipo, horas, hora_fixa in especificacao:
        candidatos = _inicios_possiveis(indice, horas, hora_fixa)
        rng.shuffle(candidatos)
        colocados = 0
        for i in candidatos:
            if colocados == por_tipo:
                break
            lo, hi = max(i - 1, 0), min(i + horas + 1, len(valores))
            if ocupado[lo:hi].any() or np.isnan(valores[i : i + horas]).any():
                continue
            if tipo == PICO:
                valores[i] += FATOR_PICO * p95_treino
            elif tipo == ELEVACAO:
                valores[i : i + horas] += FATOR_ELEVACAO * p95_treino
            else:
                valores[i : i + horas] = np.maximum(valores[i : i + horas], p95_treino)
            ocupado[i : i + horas] = True
            eventos.append(
                EventoInjetado(tipo, pd.Timestamp(indice[i]), pd.Timestamp(indice[i]) + pd.Timedelta(hours=horas))
            )
            colocados += 1
        if colocados < por_tipo:
            raise ValueError(f"nao coube {por_tipo} evento(s) do tipo {tipo}: colocados {colocados}")
    return pd.Series(valores, index=serie.index, name=serie.name), eventos


def zona_contaminada(
    indice: pd.DatetimeIndex, eventos: list[EventoInjetado], horas_defasagem: tuple[int, ...], janela: int
) -> np.ndarray:
    """Horas cujo features de historico enxergam um evento (eventos + `+1..janela` + defasagens).

    Serve para tirar do denominador de falso alarme as horas em que um modelo com lag poderia
    reagir ao evento injetado.
    """
    mascara = np.zeros(len(indice), dtype=bool)
    for ev in eventos:
        dentro = np.asarray((indice >= ev.inicio) & (indice < ev.fim))
        pos = np.flatnonzero(dentro)
        for p in pos:
            mascara[p] = True
            for d in range(1, janela + 1):
                if p + d < len(mascara):
                    mascara[p + d] = True
            for d in horas_defasagem:
                if p + d < len(mascara):
                    mascara[p + d] = True
    return mascara
