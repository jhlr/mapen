"""Features de defasagem sobre calendario completo.

O lag e calculado depois de reindexar a serie ao calendario completo: uma
lacuna aparece como NaN e nunca e pulada por um shift posicional.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from mapen_aconselhamento.ingest import reindexar


def adicionar_lags(
    dados: pd.DataFrame, coluna: str, defasagens: Sequence[int], freq: str
) -> pd.DataFrame:
    """Devolve a serie no calendario completo com colunas ``{coluna}_lag{n}``.

    ``n`` conta periodos de ``freq`` no calendario. Ponto sem leitura e NaN
    e propaga NaN para o lag que o referencia.
    """
    if any(n <= 0 for n in defasagens):
        raise ValueError("defasagens devem ser inteiros positivos")
    completo = reindexar(dados[[coluna]], freq)
    for n in defasagens:
        completo[f"{coluna}_lag{n}"] = completo[coluna].shift(n)
    return completo
