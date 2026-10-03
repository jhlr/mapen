"""Chaves de comando por dispositivo.

`ChaveDerivada` usa a mesma funcao publica da plataforma (`derivar_chave_comando`), com o segredo
mestre e o sal do dispositivo; `ChaveFixa` recebe a chave ja derivada (a que o provisionamento devolve).
"""

from __future__ import annotations

from collections.abc import Mapping

from mapen_plataforma.domain.credenciais import derivar_chave_comando
from mapen_simulador.domain.erros import ErroSimulador


class ChaveDerivada:
    def __init__(self, segredo_mestre: bytes, sais: Mapping[str, str]) -> None:
        self._segredo = segredo_mestre
        self._sais = dict(sais)

    def chave(self, device_id: str) -> bytes:
        sal = self._sais.get(device_id)
        if sal is None:
            raise ErroSimulador(f"sem sal conhecido para o dispositivo {device_id!r}")
        return derivar_chave_comando(self._segredo, device_id, sal)


class ChaveFixa:
    def __init__(self, chaves_hex: Mapping[str, str]) -> None:
        self._chaves = {k: bytes.fromhex(v) for k, v in chaves_hex.items()}

    def chave(self, device_id: str) -> bytes:
        chave = self._chaves.get(device_id)
        if chave is None:
            raise ErroSimulador(f"sem chave conhecida para o dispositivo {device_id!r}")
        return chave
