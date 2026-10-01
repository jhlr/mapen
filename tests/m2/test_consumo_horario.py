"""GET /consumo/horario: kW por hora com a faixa tarifaria do M1."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from ambiente import Ambiente, bearer
from mapen_aconselhamento.tarifa import Tarifas

DIA = "inicio=2026-10-05T00:00:00-03:00&fim=2026-10-06T00:00:00-03:00"


def _horario(amb: Ambiente, consulta: str = DIA, **extra: str) -> Any:
    sufixo = "".join(f"&{k}={v}" for k, v in extra.items())
    return amb.client.get(f"/consumo/horario?sensor_id=sa&{consulta}{sufixo}", headers=amb.ha)


def test_serie_horaria_em_kw_com_faixa_branca(amb: Ambiente) -> None:
    resposta = _horario(amb)
    assert resposta.status_code == 200
    assert resposta.json() == [
        {"hora": "2026-10-05T17:00:00-03:00", "kw": pytest.approx(2.0), "faixa": "intermediario"},
        {"hora": "2026-10-05T18:00:00-03:00", "kw": pytest.approx(2.0), "faixa": "ponta"},
    ]


def test_faixa_vem_do_m1_e_a_convencional_e_unica(amb: Ambiente) -> None:
    faixas = [p["faixa"] for p in _horario(amb, modalidade="convencional").json()]
    assert faixas == ["unico", "unico"]
    esperado = Tarifas.carregar().faixas(pd.DatetimeIndex(["2026-10-05 17:00", "2026-10-05 18:00"]), "branca")
    assert [p["faixa"] for p in _horario(amb).json()] == list(esperado)


def test_kw_e_a_media_da_hora_somando_equipamentos(amb: Ambiente) -> None:
    corpo: dict[str, Any] = {
        "leituras": [{"equipamento": "Light", "ts": "2026-10-05T17:30:00-03:00", "kwh": 0.5}]
    }
    assert amb.client.post("/sensores/sa/leituras", json=corpo, headers=bearer(amb.tokens["sa"])).status_code == 200
    primeira = _horario(amb).json()[0]
    assert primeira["kw"] == pytest.approx(2.5)


def test_periodo_sem_dado_devolve_lista_vazia(amb: Ambiente) -> None:
    assert _horario(amb, "inicio=2026-11-01T00:00:00-03:00&fim=2026-11-02T00:00:00-03:00").json() == []


def test_o_periodo_respeita_o_fuso_informado(amb: Ambiente) -> None:
    # 17:00 local = 20:00 UTC; pedir so a janela UTC 20:00-21:00 traz exatamente a hora das 17h locais.
    resposta = _horario(amb, "inicio=2026-10-05T20:00:00%2B00:00&fim=2026-10-05T21:00:00%2B00:00")
    assert [p["hora"] for p in resposta.json()] == ["2026-10-05T17:00:00-03:00"]


@pytest.mark.parametrize(
    "consulta",
    [
        "inicio=2026-10-06T00:00:00-03:00&fim=2026-10-05T00:00:00-03:00",
        "inicio=2026-09-01T00:00:00-03:00&fim=2026-10-05T00:00:00-03:00",
    ],
)
def test_periodo_invalido_ou_longo_demais(amb: Ambiente, consulta: str) -> None:
    assert _horario(amb, consulta).status_code == 422


def test_modalidade_invalida_e_sensor_inexistente(amb: Ambiente) -> None:
    assert _horario(amb, modalidade="xyz").status_code == 422
    inexistente = amb.client.get(f"/consumo/horario?sensor_id=nao-existe&{DIA}", headers=amb.ha)
    assert inexistente.status_code == 404


def test_exige_autenticacao(amb: Ambiente) -> None:
    assert amb.client.get(f"/consumo/horario?sensor_id=sa&{DIA}").status_code == 401
