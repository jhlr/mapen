from __future__ import annotations

import pandas as pd
import pytest

from mapen_aconselhamento.recomenda import ConfigEquipamentos, Regra, recomendar
from mapen_aconselhamento.tarifa import Tarifas


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
    recs = recomendar(custos, Tarifas.carregar(), _config())
    assert [r.equipamento_id for r in recs] == ["AC1"]
    # 10 kWh x 50% x (1,62479 - 0,66447) = 4,8016
    assert recs[0].economia_rs == pytest.approx(4.8016)


def test_sem_economia_quando_origem_ja_e_a_mais_barata() -> None:
    custos = pd.DataFrame(
        {"equipamento_id": ["AC1"], "faixa": ["fora_ponta"], "kwh": [10.0], "custo_rs": [6.6]}
    )
    assert recomendar(custos, Tarifas.carregar(), _config()) == []


def test_config_yaml_marca_ac_flexivel_e_iluminacao_nao() -> None:
    config = ConfigEquipamentos.carregar()
    assert config.para("z2_AC3").flexivel
    assert not config.para("z2_Light").flexivel
    assert not config.para("z2_Plug").flexivel
