"""Regras de calendario e lacunas das series: reindexacao completa e timestamps duplicados.

Cada serie e reindexada a um calendario completo; pontos que faltam viram NaN. Nunca ha
interpolacao.

Timestamps duplicados nunca sao descartados em silencio: por padrao falha com
`TimestampsDuplicadosError`; com `duplicados="primeiro"` mantem a primeira ocorrencia e a
quantidade descartada e devolvida para quem registra a carga.
Os timestamps sao ingenuos (sem fuso): horario de verao nao e tratado.
"""

from __future__ import annotations

import pandas as pd

DUPLICADOS_ERRO = "erro"
DUPLICADOS_PRIMEIRO = "primeiro"
POLITICAS_DUPLICADOS: tuple[str, str] = (DUPLICADOS_ERRO, DUPLICADOS_PRIMEIRO)


class TimestampsDuplicadosError(ValueError):
    """A serie tem timestamps repetidos e a politica e `erro`."""


def calendario(
    inicio: pd.Timestamp, fim: pd.Timestamp, freq: str
) -> pd.DatetimeIndex:
    """Calendario completo [inicio, fim) na frequencia dada."""
    return pd.date_range(inicio, fim, freq=freq, inclusive="left")


def tratar_duplicados(dados: pd.DataFrame, politica: str) -> tuple[pd.DataFrame, int]:
    """Ordena por tempo e resolve timestamps repetidos conforme `politica`.

    `erro` (padrao): levanta `TimestampsDuplicadosError` com a contagem. `primeiro`: mantem a
    primeira ocorrencia. Devolve (dados sem repeticao, quantidade de linhas repetidas).
    """
    if politica not in POLITICAS_DUPLICADOS:
        raise ValueError(f"politica de duplicados desconhecida: {politica!r}")
    repetidos = dados.index.duplicated(keep="first")
    quantidade = int(repetidos.sum())
    if quantidade and politica == DUPLICADOS_ERRO:
        exemplos = ", ".join(str(t) for t in dados.index[repetidos][:3])
        raise TimestampsDuplicadosError(
            f"{quantidade} timestamps duplicados (ex.: {exemplos}); "
            f"use duplicados={DUPLICADOS_PRIMEIRO!r} para manter a primeira ocorrencia"
        )
    return dados[~repetidos].sort_index(), quantidade


def reindexar(
    dados: pd.DataFrame, freq: str, inicio: pd.Timestamp | None = None, fim: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Reindexa `dados` (indice temporal sem repeticao) ao calendario completo; lacunas ficam NaN.

    `fim` e exclusivo. Sem `inicio`/`fim`, usa o primeiro e o ultimo timestamp presentes.
    Duplicados levantam `TimestampsDuplicadosError`: trate-os antes com `tratar_duplicados`.
    """
    unico, _ = tratar_duplicados(dados, DUPLICADOS_ERRO)
    if inicio is None:
        inicio = pd.Timestamp(unico.index.min())
    if fim is None:
        fim = pd.Timestamp(unico.index.max()) + pd.Timedelta(freq)
    return unico.reindex(calendario(inicio, fim, freq))
