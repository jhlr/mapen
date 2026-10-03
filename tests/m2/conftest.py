from __future__ import annotations

import pytest

from ambiente import Ambiente, montar


@pytest.fixture
def amb() -> Ambiente:
    return montar(habilitado=True)


@pytest.fixture
def amb_flag_off() -> Ambiente:
    return montar(habilitado=False)
