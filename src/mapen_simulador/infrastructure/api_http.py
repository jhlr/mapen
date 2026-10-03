"""Cliente httpx da API da plataforma: leituras (token do dispositivo) e comandos (Bearer da empresa)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

import httpx

from mapen_plataforma.domain.comando import ComandoRele
from mapen_simulador.application.portas import RespostaComando
from mapen_simulador.domain.amostras import LoteLeituras
from mapen_simulador.domain.eventos import EventoDispositivo


class RespostaHttp(Protocol):
    @property
    def status_code(self) -> int: ...

    def json(self) -> object: ...


class ClienteHttp(Protocol):
    """O que o simulador usa de um cliente HTTP (`httpx.Client` e o `TestClient` do FastAPI servem)."""

    def post(self, url: str, *, json: object, headers: Mapping[str, str]) -> RespostaHttp: ...


class EnvioLeiturasHttp:
    """POST /sensores/{id}/leituras. Qualquer falha de transporte ou status != 200 e 'nao confirmado'."""

    def __init__(self, client: ClienteHttp, sensor_id: str, token: str) -> None:
        self._client = client
        self._sensor_id = sensor_id
        self._token = token

    def enviar(self, lote: LoteLeituras) -> bool:
        corpo = {
            "leituras": [
                {
                    "equipamento": a.equipamento,
                    "ts": a.ts.isoformat(),
                    "potencia_w": a.potencia_w,
                    "kwh": a.kwh,
                }
                for a in lote.amostras
            ]
        }
        try:
            resposta = self._client.post(
                f"/sensores/{self._sensor_id}/leituras",
                json=corpo,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.TransportError:
            return False
        return resposta.status_code == 200


class EnvioEventosHttp:
    """POST /sensores/{id}/eventos com o token do dispositivo. So status 200 e 'confirmado'."""

    def __init__(self, client: ClienteHttp, sensor_id: str, token: str) -> None:
        self._client = client
        self._sensor_id = sensor_id
        self._token = token

    def enviar(self, eventos: Sequence[EventoDispositivo]) -> bool:
        corpo = {
            "eventos": [
                {
                    "tipo": e.tipo.value,
                    "inicio": e.inicio.isoformat(),
                    "fim": None if e.fim is None else e.fim.isoformat(),
                    "duracao_s": e.duracao_s,
                    "bateria_esgotada": e.bateria_esgotada,
                }
                for e in eventos
            ]
        }
        try:
            resposta = self._client.post(
                f"/sensores/{self._sensor_id}/eventos",
                json=corpo,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.TransportError:
            return False
        return resposta.status_code == 200


class EnvioComandoHttp:
    """POST /desligamentos com `Authorization: Bearer <chave da empresa>`."""

    def __init__(self, client: ClienteHttp, chave_api: str) -> None:
        self._client = client
        self._chave_api = chave_api

    def enviar(
        self, comando: ComandoRele, equipamento_id: str, origem: str, regra_id: str | None
    ) -> RespostaComando:
        corpo: dict[str, object] = {
            "equipamento_id": equipamento_id,
            "origem": origem,
            "comando": {
                "device_id": comando.device_id,
                "acao": comando.acao.value,
                "nonce": comando.nonce,
                "emitido_em": comando.emitido_em.isoformat(),
                "validade": comando.validade.isoformat(),
                "assinatura": comando.assinatura,
            },
        }
        if regra_id is not None:
            corpo["regra_id"] = regra_id
        resposta = self._client.post(
            "/desligamentos", json=corpo, headers={"Authorization": f"Bearer {self._chave_api}"}
        )
        dados = resposta.json()
        motivo = dados.get("motivo") if isinstance(dados, dict) else None
        return RespostaComando(resposta.status_code == 200, resposta.status_code, motivo if isinstance(motivo, str) else None)
