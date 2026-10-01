"""Decisao de anomalia a partir do residuo padronizado."""

from __future__ import annotations

import numpy as np

LIMIAR_Z_PADRAO = 4.0


def decidir_anomalia(z: np.ndarray, limiar: float = LIMIAR_Z_PADRAO) -> np.ndarray:
    """True onde |z| >= limiar. NaN (sem dado ou sem feature) nunca e anomalia."""
    if limiar <= 0:
        raise ValueError("limiar deve ser positivo")
    with np.errstate(invalid="ignore"):
        return np.asarray(np.abs(z) >= limiar)
