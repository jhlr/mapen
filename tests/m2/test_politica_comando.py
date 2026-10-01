"""Politica de seguranca do comando de rele (dominio puro, sem I/O)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mapen_plataforma.domain.comando import (
    ESTADO_INICIAL,
    Acao,
    ComandoRele,
    ConfiguracaoSeguranca,
    EstadoRele,
    Motivo,
    assinar,
    avaliar_comando,
)
from mapen_plataforma.domain.entidades import Equipamento, ErroDominio

AGORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
CHAVE = b"k"
LIGADO = ConfiguracaoSeguranca(True)
EQ = Equipamento("e1", "emp", "dev1", "AC1", critico=False)


def _cmd(nonce: str = "n", validade: datetime = AGORA + timedelta(seconds=30), chave: bytes = CHAVE) -> ComandoRele:
    return ComandoRele("dev1", Acao.DESLIGAR, nonce, validade, assinar(chave, "dev1", Acao.DESLIGAR, nonce, validade))


def _avaliar(
    cmd: ComandoRele,
    *,
    eq: Equipamento = EQ,
    nonce_repetido: bool = False,
    autorizado_por: str | None = "joao",
    config: ConfiguracaoSeguranca = LIGADO,
    chave: bytes | None = CHAVE,
) -> tuple[bool, Motivo | None]:
    d = avaliar_comando(cmd, chave, AGORA, nonce_repetido, eq, autorizado_por, config)
    return d.aceito, d.motivo


def test_caminho_feliz_com_flag_ligada() -> None:
    assert _avaliar(_cmd()) == (True, None)


def test_assinatura_invalida() -> None:
    assert _avaliar(_cmd(chave=b"outra")) == (False, Motivo.ASSINATURA_INVALIDA)


def test_adulterar_a_acao_invalida_a_assinatura() -> None:
    original = _cmd()
    adulterado = ComandoRele(original.device_id, Acao.LIGAR, original.nonce, original.validade, original.assinatura)
    assert _avaliar(adulterado) == (False, Motivo.ASSINATURA_INVALIDA)


def test_dispositivo_sem_chave() -> None:
    assert _avaliar(_cmd(), chave=None) == (False, Motivo.ASSINATURA_INVALIDA)


def test_nonce_repetido() -> None:
    assert _avaliar(_cmd(), nonce_repetido=True) == (False, Motivo.NONCE_REPETIDO)


def test_validade_vencida() -> None:
    assert _avaliar(_cmd(validade=AGORA - timedelta(seconds=1))) == (False, Motivo.VALIDADE_VENCIDA)


def test_equipamento_critico() -> None:
    critico = Equipamento("e2", "emp", "dev1", "UTI", critico=True)
    assert _avaliar(_cmd(), eq=critico) == (False, Motivo.EQUIPAMENTO_CRITICO)


@pytest.mark.parametrize("autorizado", [None, "", "   "])
def test_sem_autorizacao(autorizado: str | None) -> None:
    assert _avaliar(_cmd(), autorizado_por=autorizado) == (False, Motivo.SEM_AUTORIZACAO)


def test_flag_global_desligada_por_padrao_rejeita_desligamento() -> None:
    assert ConfiguracaoSeguranca().desligamento_remoto_habilitado is False
    assert _avaliar(_cmd(), config=ConfiguracaoSeguranca()) == (False, Motivo.DESLIGAMENTO_REMOTO_DESABILITADO)


def test_flag_desligada_nao_bloqueia_religar() -> None:
    cmd = ComandoRele("dev1", Acao.LIGAR, "n", AGORA + timedelta(seconds=5), assinar(CHAVE, "dev1", Acao.LIGAR, "n", AGORA + timedelta(seconds=5)))
    assert _avaliar(cmd, config=ConfiguracaoSeguranca()) == (True, None)


def test_dispositivo_divergente_do_equipamento() -> None:
    outro = Equipamento("e3", "emp", "dev2", "AC9")
    assert _avaliar(_cmd(), eq=outro) == (False, Motivo.DISPOSITIVO_DIVERGENTE)


def test_validade_sem_fuso_e_erro() -> None:
    with pytest.raises(ErroDominio):
        ComandoRele("dev1", Acao.DESLIGAR, "n", datetime(2026, 10, 5, 12, 0), "x")


def test_estado_inicial_do_rele_e_energizado() -> None:
    assert ESTADO_INICIAL is EstadoRele.ENERGIZADO
