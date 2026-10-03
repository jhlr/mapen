from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mapen_aconselhamento.domain.equipamentos import ALTA, BAIXA, ConfigEquipamentos, Regra
from mapen_aconselhamento.domain.recomendacao import recomendar
from mapen_aconselhamento.infrastructure.equipamentos_yaml import carregar_config_equipamentos
from mapen_aconselhamento.infrastructure.tarifa_csv import carregar_tarifas


def _config() -> ConfigEquipamentos:
    flex = Regra("ar_condicionado", True, False, 0.5)
    fixo = Regra("iluminacao", False, False, 0.5)
    critico = Regra("critico", True, True, 0.5)
    return ConfigEquipamentos(
        regras=(("AC*", flex), ("LUZ*", fixo), ("CRIT*", critico)), padrao=Regra("x", False, False, 0.0)
    )


def test_recomenda_somente_flexivel() -> None:
    custos = pd.DataFrame(
        {
            "equipamento_id": ["AC1", "LUZ1", "CRIT1", "DESCONHECIDO"],
            "faixa": ["ponta"] * 4,
            "kwh": [10.0, 10.0, 10.0, 10.0],
            "custo_rs": [16.2479] * 4,
        }
    )
    recs = recomendar(custos, carregar_tarifas(), _config())
    assert [r.equipamento_id for r in recs] == ["AC1"]
    # 10 kWh x 50% x (1,62479 - 0,66447) = 4,8016
    assert recs[0].economia_rs == pytest.approx(4.8016)


def test_sem_economia_quando_origem_ja_e_a_mais_barata() -> None:
    custos = pd.DataFrame(
        {"equipamento_id": ["AC1"], "faixa": ["fora_ponta"], "kwh": [10.0], "custo_rs": [6.6]}
    )
    assert recomendar(custos, carregar_tarifas(), _config()) == []


def test_config_yaml_valores_sourced() -> None:
    config = carregar_config_equipamentos()
    ac = config.para("z2_AC3")
    assert ac.flexivel and not ac.critico
    assert ac.fracao_movivel == pytest.approx(0.18)  # central, docs/m1_premissas.md
    assert ac.fracao(BAIXA) == pytest.approx(0.10)
    assert ac.fracao(ALTA) == pytest.approx(0.25)
    for ident in ("z2_Light", "z2_Plug"):
        regra = config.para(ident)
        assert not regra.flexivel and not regra.critico and regra.fracao_movivel == 0.0


def test_glob_ac_nao_casa_ids_como_access() -> None:
    config = carregar_config_equipamentos()
    assert not config.para("z1_ACCESS").flexivel
    assert not config.para("z1_AC").flexivel
    assert config.para("z1_AC12").flexivel


@pytest.mark.parametrize("valor", ["0", "-0.1", "1.5", ".nan", ".inf", "abc"])
def test_fracao_movivel_invalida_e_rejeitada_no_carregamento(tmp_path: Path, valor: str) -> None:
    yaml_ruim = tmp_path / "e.yaml"
    yaml_ruim.write_text(
        f'equipamentos:\n  - padrao: "*_AC[0-9]*"\n    flexivel: true\n    fracao_movivel: {valor}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fracao_movivel"):
        carregar_config_equipamentos(yaml_ruim)


def test_regra_flexivel_sem_fracao_e_rejeitada(tmp_path: Path) -> None:
    yaml_ruim = tmp_path / "e.yaml"
    yaml_ruim.write_text('equipamentos:\n  - padrao: "AC*"\n    flexivel: true\n', encoding="utf-8")
    with pytest.raises(ValueError, match="exige fracao_movivel"):
        carregar_config_equipamentos(yaml_ruim)
