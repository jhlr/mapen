"""Eventos que o dispositivo mede no proprio relogio (ultimo suspiro, queda de energia, falha de conexao)."""

from __future__ import annotations

from typing import Any

import pytest

from ambiente import Ambiente, bearer

# AGORA do ambiente = 2026-10-05T12:00:00Z. A queda de energia vai de 11:00 a 11:15 UTC (08:00 a 08:15 em Recife).
SUSPIRO = {"tipo": "ultimo_suspiro", "inicio": "2026-10-05T08:00:00-03:00"}
QUEDA = {
    "tipo": "queda_energia", "inicio": "2026-10-05T08:00:00-03:00", "fim": "2026-10-05T08:15:00-03:00",
    "duracao_s": 900.45, "bateria_esgotada": False,
}
FALHA = {"tipo": "falha_conexao", "inicio": "2026-10-05T07:00:00-03:00", "fim": "2026-10-05T07:10:00-03:00", "duracao_s": 600.0}


def _enviar(amb: Ambiente, eventos: list[dict[str, Any]], sensor: str = "sa", token: str | None = None) -> Any:
    chave = token if token is not None else amb.tokens[sensor]
    return amb.client.post(f"/sensores/{sensor}/eventos", json={"eventos": eventos}, headers=bearer(chave))


def _log(amb: Ambiente, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    resposta = amb.client.get("/eventos", headers=headers if headers is not None else amb.ha)
    assert resposta.status_code == 200
    lista: list[dict[str, Any]] = resposta.json()
    return lista


def test_grava_ultimo_suspiro_e_queda_com_o_instante_do_relogio_do_dispositivo(amb: Ambiente) -> None:
    r = _enviar(amb, [SUSPIRO, QUEDA])
    assert r.status_code == 200 and r.json() == {"gravados": 2, "duplicados": 0}
    por_tipo = {e["tipo"]: e for e in _log(amb)}
    suspiro, queda = por_tipo["ultimo_suspiro"], por_tipo["queda_energia"]
    assert suspiro["ts"].startswith("2026-10-05T11:00:00") and suspiro["sensor_id"] == "sa"
    assert suspiro["origem"] == "dispositivo" and suspiro["autorizado_por"] is None and suspiro["regra_id"] is None
    assert suspiro["payload"]["bateria_esgotada"] == "false" and "fim" not in suspiro["payload"]
    assert queda["payload"]["duracao_s"] == "900.45" and queda["payload"]["fim"].startswith("2026-10-05T11:15:00")
    # o relogio da plataforma fica ao lado do do dispositivo: o desvio entre os dois e visivel
    assert queda["payload"]["recebido_em"].startswith("2026-10-05T12:00:00")


def test_reenvio_do_mesmo_lote_nao_duplica(amb: Ambiente) -> None:
    assert _enviar(amb, [SUSPIRO, QUEDA]).json() == {"gravados": 2, "duplicados": 0}
    amb.relogio.avancar(1800)  # outra tentativa, mais tarde
    assert _enviar(amb, [SUSPIRO, QUEDA, FALHA]).json() == {"gravados": 1, "duplicados": 2}
    assert len(_log(amb)) == 3


def test_mesmo_instante_com_outro_fuso_e_o_mesmo_evento(amb: Ambiente) -> None:
    assert _enviar(amb, [SUSPIRO]).json()["gravados"] == 1
    mesmo_em_utc = {"tipo": "ultimo_suspiro", "inicio": "2026-10-05T11:00:00Z"}
    assert _enviar(amb, [mesmo_em_utc]).json() == {"gravados": 0, "duplicados": 1}


def test_instantes_diferentes_ou_tipos_diferentes_sao_eventos_diferentes(amb: Ambiente) -> None:
    depois = {**SUSPIRO, "inicio": "2026-10-05T08:00:01-03:00"}
    assert _enviar(amb, [SUSPIRO, depois, {**QUEDA, "inicio": SUSPIRO["inicio"]}]).json()["gravados"] == 3


def test_lote_vazio_e_aceito(amb: Ambiente) -> None:
    assert _enviar(amb, []).json() == {"gravados": 0, "duplicados": 0}


def test_ultimo_suspiro_sem_rtc_e_queda_sem_duracao_sao_aceitos(amb: Ambiente) -> None:
    sem_rtc = {"tipo": "queda_energia", "inicio": "2026-10-05T08:00:00-03:00", "bateria_esgotada": True}
    assert _enviar(amb, [sem_rtc]).json()["gravados"] == 1
    e = _log(amb)[0]
    assert e["payload"]["bateria_esgotada"] == "true" and "duracao_s" not in e["payload"] and "fim" not in e["payload"]


# ---------------------------------------------------------------- autenticacao e isolamento


def test_sem_token_com_chave_de_empresa_ou_token_de_outro_sensor_e_401(amb: Ambiente) -> None:
    corpo = {"eventos": [SUSPIRO]}
    assert amb.client.post("/sensores/sa/eventos", json=corpo).status_code == 401
    assert amb.client.post("/sensores/sa/eventos", json=corpo, headers=amb.ha).status_code == 401
    assert _enviar(amb, [SUSPIRO], sensor="sa", token=amb.tokens["sb"]).status_code == 401
    assert _enviar(amb, [SUSPIRO], sensor="sb", token=amb.tokens["sa"]).status_code == 401
    assert _log(amb) == [] and _log(amb, amb.hb) == []


def test_evento_entra_so_no_log_da_empresa_dona_do_sensor(amb: Ambiente) -> None:
    assert _enviar(amb, [SUSPIRO], sensor="sb").json()["gravados"] == 1
    assert [e["sensor_id"] for e in _log(amb, amb.hb)] == ["sb"]
    assert _log(amb) == []


# ---------------------------------------------------------------- validacao


@pytest.mark.parametrize("evento", [
    {"tipo": "desligamento_executado", "inicio": SUSPIRO["inicio"]},  # tipo que so a plataforma gera
    {"tipo": "comando_rejeitado", "inicio": SUSPIRO["inicio"]},
    {"tipo": "outro", "inicio": SUSPIRO["inicio"]},
    {"tipo": "ultimo_suspiro", "inicio": "2026-10-05T08:00:00"},  # sem fuso
    {**QUEDA, "fim": "2026-10-05T07:59:59-03:00"},  # fim antes do inicio
    {**QUEDA, "duracao_s": -1.0},
    {**QUEDA, "duracao_s": "abc"},
    {**SUSPIRO, "fim": "2026-10-05T08:15:00-03:00"},  # ultimo suspiro marca so o inicio
    {**SUSPIRO, "duracao_s": 5.0},
    {**QUEDA, "autorizado_por": "alguem"},  # campo desconhecido
    {**QUEDA, "equipamento_id": "eq-ac"},
    {**QUEDA, "origem": "usuario"},
    {**QUEDA, "bateria_esgotada": "talvez"},
    {"inicio": SUSPIRO["inicio"]},
])
def test_evento_invalido_e_422_e_nada_e_gravado(amb: Ambiente, evento: dict[str, Any]) -> None:
    assert _enviar(amb, [evento]).status_code == 422
    assert _log(amb) == []


def test_lote_com_um_evento_invalido_nao_grava_nenhum(amb: Ambiente) -> None:
    assert _enviar(amb, [SUSPIRO, {**QUEDA, "duracao_s": -1.0}]).status_code == 422
    assert _log(amb) == []


@pytest.mark.parametrize("longe", [
    {"tipo": "ultimo_suspiro", "inicio": "2026-10-07T12:00:00Z"},
    {**QUEDA, "fim": "2026-10-07T12:00:00Z"},
])
def test_instante_no_futuro_alem_de_um_dia_e_422_e_dentro_da_tolerancia_e_aceito(amb: Ambiente, longe: dict[str, Any]) -> None:
    r = _enviar(amb, [longe])
    assert r.status_code == 422 and "futuro" in r.json()["detail"]
    assert _log(amb) == []
    perto = {**QUEDA, "inicio": "2026-10-06T08:00:00Z", "fim": "2026-10-06T08:15:00Z"}
    assert _enviar(amb, [perto]).status_code == 200


def test_lote_acima_de_100_eventos_e_422(amb: Ambiente) -> None:
    def evento(i: int) -> dict[str, Any]:
        return {"tipo": "falha_conexao", "inicio": f"2026-10-05T0{i // 60}:{i % 60:02d}:00Z"}

    assert _enviar(amb, [evento(i) for i in range(100)]).json() == {"gravados": 100, "duplicados": 0}
    assert _enviar(amb, [evento(i) for i in range(101)]).status_code == 422


def test_nan_na_duracao_e_recusado_sem_ecoar_o_valor(amb: Ambiente) -> None:
    r = amb.client.post(
        "/sensores/sa/eventos", headers=bearer(amb.tokens["sa"]),
        content='{"eventos": [{"tipo": "queda_energia", "inicio": "2026-10-05T08:00:00Z", "duracao_s": NaN}]}',
    )
    assert r.status_code == 422 and "NaN" not in r.text
