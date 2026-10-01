"""Regra de emissao de comando assinado. A canonicalizacao e o HMAC sao os da plataforma (nao duplicados)."""

from __future__ import annotations

from datetime import datetime, timedelta

from mapen_plataforma.domain.comando import MAX_TTL, Acao, ComandoRele, assinar
from mapen_simulador.domain.erros import ErroSimulador


def construir_comando(
    chave: bytes,
    device_id: str,
    empresa_id: str,
    equipamento_id: str,
    acao: Acao,
    nonce: str,
    emitido_em: datetime,
    validade_s: float,
) -> ComandoRele:
    """Comando assinado com validade positiva e no maximo `MAX_TTL` (60 s)."""
    if not 0 < validade_s <= MAX_TTL.total_seconds():
        raise ErroSimulador(f"validade deve ficar entre 0 e {MAX_TTL.total_seconds():.0f} s")
    validade = emitido_em + timedelta(seconds=validade_s)
    assinatura = assinar(chave, device_id, empresa_id, equipamento_id, acao, nonce, emitido_em, validade)
    return ComandoRele(device_id, empresa_id, equipamento_id, acao, nonce, emitido_em, validade, assinatura)
