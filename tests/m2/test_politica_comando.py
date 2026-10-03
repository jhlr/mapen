"""Politica de seguranca do comando de rele (dominio puro, sem I/O)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from mapen_plataforma.domain.comando import (
    ESTADO_INICIAL,
    MAX_TTL,
    TOLERANCIA_RELOGIO,
    Acao,
    ComandoRele,
    ConfiguracaoSeguranca,
    EstadoRele,
    Motivo,
    assinar,
    avaliar_comando,
    mensagem_assinada,
)
from mapen_plataforma.domain.entidades import Equipamento, ErroDominio

AGORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
CHAVE = b"k"
LIGADO = ConfiguracaoSeguranca(True)
EQ = Equipamento("e1", "emp", "dev1", "AC1", critico=False)


def _cmd(
    nonce: str = "n",
    emitido: datetime = AGORA,
    validade: datetime = AGORA + timedelta(seconds=30),
    chave: bytes = CHAVE,
    acao: Acao = Acao.DESLIGAR,
    equipamento_id: str = "e1",
    empresa_id: str = "emp",
    assinatura: str | None = None,
) -> ComandoRele:
    sig = assinar(chave, "dev1", empresa_id, equipamento_id, acao, nonce, emitido, validade)
    return ComandoRele("dev1", empresa_id, equipamento_id, acao, nonce, emitido, validade, sig if assinatura is None else assinatura)


def _avaliar(
    cmd: ComandoRele,
    *,
    eq: Equipamento = EQ,
    nonce_novo: bool = True,
    regra_valida: bool = True,
    autorizado_por: str | None = "joao",
    config: ConfiguracaoSeguranca = LIGADO,
    chave: bytes | None = CHAVE,
    agora: datetime = AGORA,
) -> tuple[bool, Motivo | None]:
    d = avaliar_comando(cmd, chave, agora, lambda: nonce_novo, eq, regra_valida, autorizado_por, config)
    return d.aceito, d.motivo


def test_caminho_feliz_com_flag_ligada() -> None:
    """Guarda: se o caminho feliz for rejeitado por qualquer endurecimento novo, este teste falha."""
    assert _avaliar(_cmd()) == (True, None)
    assert _avaliar(_cmd(validade=AGORA + MAX_TTL)) == (True, None)


def test_assinatura_invalida() -> None:
    assert _avaliar(_cmd(chave=b"outra")) == (False, Motivo.ASSINATURA_INVALIDA)


@pytest.mark.parametrize("lixo", ["é" * 64, "😀" * 32, "", "zz", "A" * 64, "0" * 63])
def test_assinatura_malformada_ou_nao_ascii_e_rejeitada_sem_excecao(lixo: str) -> None:
    assert _avaliar(_cmd(assinatura=lixo)) == (False, Motivo.ASSINATURA_INVALIDA)


def test_adulterar_a_acao_invalida_a_assinatura() -> None:
    original = _cmd()
    adulterado = ComandoRele(
        original.device_id, original.empresa_id, original.equipamento_id, Acao.LIGAR, original.nonce,
        original.emitido_em, original.validade, original.assinatura,
    )
    assert _avaliar(adulterado) == (False, Motivo.ASSINATURA_INVALIDA)


def test_a_assinatura_amarra_empresa_e_equipamento() -> None:
    """Um comando assinado para o equipamento X nao serve para o equipamento Y nem para outra empresa."""
    original = _cmd()
    assert _avaliar(replace(original, equipamento_id="e9")) == (False, Motivo.ASSINATURA_INVALIDA)
    assert _avaliar(replace(original, empresa_id="outra")) == (False, Motivo.ASSINATURA_INVALIDA)


def test_mensagem_assinada_e_json_canonico() -> None:
    bruto = mensagem_assinada("d", "e", "q", Acao.LIGAR, "n", AGORA, AGORA + timedelta(seconds=9)).decode()
    assert " " not in bruto
    dados = json.loads(bruto)
    assert list(dados) == sorted(dados)
    assert set(dados) == {"device_id", "empresa_id", "equipamento_id", "acao", "nonce", "emitido_em", "validade"}


def test_dispositivo_sem_chave() -> None:
    assert _avaliar(_cmd(), chave=None) == (False, Motivo.ASSINATURA_INVALIDA)


def test_nonce_repetido() -> None:
    assert _avaliar(_cmd(), nonce_novo=False) == (False, Motivo.NONCE_REPETIDO)


def test_ttl_acima_do_maximo_e_rejeitado_mesmo_com_assinatura_valida() -> None:
    longo = _cmd(validade=AGORA + MAX_TTL + timedelta(seconds=1))
    assert _avaliar(longo) == (False, Motivo.TTL_EXCESSIVO)
    anos = _cmd(validade=AGORA + timedelta(days=3 * 365))
    assert _avaliar(anos) == (False, Motivo.TTL_EXCESSIVO)


def test_validade_antes_da_emissao_e_rejeitada() -> None:
    assert _avaliar(_cmd(validade=AGORA - timedelta(seconds=1))) == (False, Motivo.TTL_EXCESSIVO)


def test_emissao_no_futuro_alem_da_tolerancia() -> None:
    futuro = AGORA + TOLERANCIA_RELOGIO + timedelta(seconds=1)
    assert _avaliar(_cmd(emitido=futuro, validade=futuro + timedelta(seconds=10))) == (False, Motivo.EMISSAO_FUTURA)
    dentro = AGORA + TOLERANCIA_RELOGIO
    assert _avaliar(_cmd(emitido=dentro, validade=dentro + timedelta(seconds=10))) == (True, None)


def test_validade_vencida_respeita_a_tolerancia_de_relogio() -> None:
    cmd = _cmd(emitido=AGORA - timedelta(seconds=40), validade=AGORA - timedelta(seconds=1))
    assert _avaliar(cmd) == (True, None)  # dentro da tolerancia
    vencido = _cmd(emitido=AGORA - timedelta(seconds=50), validade=AGORA - TOLERANCIA_RELOGIO - timedelta(seconds=1))
    assert _avaliar(vencido) == (False, Motivo.VALIDADE_VENCIDA)


@pytest.mark.parametrize(
    "cmd",
    [
        _cmd(chave=b"outra"),
        _cmd(validade=AGORA + timedelta(days=1)),
        _cmd(emitido=AGORA + timedelta(minutes=5), validade=AGORA + timedelta(minutes=5, seconds=10)),
        _cmd(emitido=AGORA - timedelta(minutes=5), validade=AGORA - timedelta(minutes=4, seconds=50)),
    ],
)
def test_comando_que_falha_assinatura_ou_ttl_nao_queima_o_nonce(cmd: ComandoRele) -> None:
    consumos: list[int] = []

    def consumir() -> bool:
        consumos.append(1)
        return True

    avaliar_comando(cmd, CHAVE, AGORA, consumir, EQ, True, "joao", LIGADO)
    assert consumos == []


def test_comando_valido_consome_o_nonce_uma_vez() -> None:
    consumos: list[int] = []

    def consumir() -> bool:
        consumos.append(1)
        return True

    assert avaliar_comando(_cmd(), CHAVE, AGORA, consumir, EQ, True, "joao", LIGADO).aceito
    assert consumos == [1]


def test_regra_invalida() -> None:
    assert _avaliar(_cmd(), regra_valida=False) == (False, Motivo.REGRA_INVALIDA)


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
    assert _avaliar(_cmd(acao=Acao.LIGAR), config=ConfiguracaoSeguranca()) == (True, None)


def test_dispositivo_divergente_do_equipamento() -> None:
    outro = Equipamento("e3", "emp", "dev2", "AC9", critico=False)
    assert _avaliar(_cmd(), eq=outro) == (False, Motivo.DISPOSITIVO_DIVERGENTE)


def test_instantes_sem_fuso_sao_erro() -> None:
    ingenuo = datetime(2026, 10, 5, 12, 0)
    with pytest.raises(ErroDominio):
        ComandoRele("dev1", "emp", "e1", Acao.DESLIGAR, "n", AGORA, ingenuo, "x")
    with pytest.raises(ErroDominio):
        ComandoRele("dev1", "emp", "e1", Acao.DESLIGAR, "n", ingenuo, AGORA, "x")


def test_estado_inicial_do_rele_e_energizado() -> None:
    assert ESTADO_INICIAL is EstadoRele.ENERGIZADO
