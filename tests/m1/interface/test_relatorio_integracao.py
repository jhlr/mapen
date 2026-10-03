from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from mapen_aconselhamento.application.relatorio_mensal import GerarRelatorioMensal
from mapen_aconselhamento.domain.equipamentos import ConfigEquipamentos
from mapen_aconselhamento.domain.tarifa import Tarifas
from mapen_aconselhamento.infrastructure.bdg2 import BDG2_ELETRICIDADE, carregar_bdg2
from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_aconselhamento.infrastructure.cu_bems import carregar_cu_bems
from mapen_aconselhamento.infrastructure.duckdb_leituras import LeiturasDuckDB, conectar
from mapen_aconselhamento.infrastructure.equipamentos_yaml import carregar_config_equipamentos
from mapen_aconselhamento.infrastructure.relatorio_arquivo import escrever_relatorio
from mapen_aconselhamento.infrastructure.tarifa_csv import carregar_tarifas
from mapen_aconselhamento.interface.relatorio_markdown import DISCLAIMER, renderizar_relatorio

CSV = RAIZ / "data" / "publicos" / "cu_bems" / "2018Floor2.csv"

PONTA, INTERM, FORA, CONV = 1.62479, 1.05341, 0.66447, 0.79886
MINUTOS_OUT_2026 = 31 * 24 * 60


def gerar_relatorio(
    con: duckdb.DuckDBPyConnection, sensor_id: str, mes: str, tarifas: Tarifas, config: ConfigEquipamentos
) -> str:
    return renderizar_relatorio(GerarRelatorioMensal(LeiturasDuckDB(con)).executar(sensor_id, mes, tarifas, config))


def _csv_sintetico(destino: Path) -> Path:
    """Outubro/2026 a 1 min: AC1 2 kW, Light 1 kW, Plug 0,5 kW constantes.

    Falta a hora sabado 2026-10-03 10:00-10:59 (60 linhas) em todas as colunas.
    """
    ts = pd.date_range("2026-10-01", "2026-11-01", freq="1min", inclusive="left")
    quadro = pd.DataFrame(
        {
            "Date": ts,
            "z1_AC1(kW)": 2.0,
            "z1_Light(kW)": 1.0,
            "z1_Plug(kW)": 0.5,
            "z1_Temp": 25.0,  # coluna ambiental: ignorada
        }
    )
    lacuna = (ts >= pd.Timestamp("2026-10-03 10:00")) & (ts < pd.Timestamp("2026-10-03 11:00"))
    quadro[~lacuna].to_csv(destino, index=False)
    return destino


def test_sintetico_ate_relatorio_numeros_exatos(tmp_path: Path) -> None:
    con = conectar()
    inicio, fim = pd.Timestamp("2026-10-01"), pd.Timestamp("2026-11-01")
    linhas = carregar_cu_bems(con, _csv_sintetico(tmp_path / "f.csv"), "sint", inicio, fim)
    assert linhas == 3 * MINUTOS_OUT_2026  # calendario completo, lacuna vira linha ausente
    assert con.execute("SELECT count(*) FROM leitura WHERE ausente").fetchone() == (180,)

    texto = gerar_relatorio(con, "sint", "2026-10", carregar_tarifas(), carregar_config_equipamentos())

    # AC1: 2 kW; 60 min ausentes (sabado, fora de ponta) = 2 kWh a menos.
    # 22 dias uteis em out/2026 - feriado 12/out (segunda) = 21 dias com ponta (3 h) e interm. (2 h).
    kwh_ponta, kwh_interm = 21 * 3 * 2.0, 21 * 2 * 2.0
    kwh_ac = (MINUTOS_OUT_2026 - 60) * 2.0 / 60
    kwh_fora = kwh_ac - kwh_ponta - kwh_interm
    assert (kwh_ponta, kwh_interm, kwh_ac, kwh_fora) == (126.0, 84.0, 1486.0, 1276.0)
    custo_conv = kwh_ac * CONV
    custo_branca = kwh_ponta * PONTA + kwh_interm * INTERM + kwh_fora * FORA
    assert f"| 1 | z1_AC1 | {kwh_ac:.1f} | {custo_conv:.2f} | {custo_branca:.2f} | sim | 0.1% |" in texto
    assert "180 de 133920" in texto
    assert "Timestamps duplicados: 0 descartados (politica `erro`)" in texto

    # Recomendacoes: 18% central, 10% baixa, 25% alta; so AC1 e flexivel.
    def eco(fracao: float) -> tuple[float, float]:
        return (
            kwh_ponta * fracao * (PONTA - FORA),
            kwh_interm * fracao * (INTERM - FORA),
        )

    linha_ponta = (
        f"| z1_AC1 | ponta | fora_ponta | {kwh_ponta * 0.18:.2f} | {eco(0.10)[0]:.2f} | "
        f"{eco(0.18)[0]:.2f} | {eco(0.25)[0]:.2f} |"
    )
    linha_interm = (
        f"| z1_AC1 | intermediario | fora_ponta | {kwh_interm * 0.18:.2f} | {eco(0.10)[1]:.2f} | "
        f"{eco(0.18)[1]:.2f} | {eco(0.25)[1]:.2f} |"
    )
    assert linha_ponta in texto and linha_interm in texto
    assert "Economia sob hipotese de 18% movel (R$)" in texto
    assert texto.count("| z1_AC1 | ") == 3  # 1 no ranking + 2 recomendacoes (ponta, interm.)
    assert f"de 18% movel: R$ {sum(eco(0.18)):.2f}" in texto

    # Ressalvas obrigatorias.
    assert "SEM tributos e SEM bandeira" in texto
    assert "Hora 21:00 (dias uteis): tratada como fora de ponta" in texto
    assert "20/nov nao esta na lista" in texto
    assert "nao de medicao brasileira" in texto
    assert "Timestamps ingenuos" in texto
    assert DISCLAIMER in texto


def test_bdg2_le_direto_do_zip(tmp_path: Path) -> None:
    zip_caminho = tmp_path / "bdg2.zip"
    csv = "timestamp,Pred_A\n2016-01-01 00:00:00,10.0\n2016-01-01 01:00:00,\n2016-01-01 03:00:00,30.0\n"
    with zipfile.ZipFile(zip_caminho, "w") as zf:
        zf.writestr("buds-lab-xyz/" + BDG2_ELETRICIDADE, csv)
    con = conectar()
    n = carregar_bdg2(con, zip_caminho, ["Pred_A"], pd.Timestamp("2016-01-01"), pd.Timestamp("2016-01-01 04:00"))
    assert n == 4  # calendario completo de 4 horas
    ausentes = con.execute("SELECT count(*) FROM leitura WHERE ausente").fetchone()
    assert ausentes == (2,)  # 01:00 (NaN no arquivo) e 02:00 (linha faltando)
    kwh = con.execute("SELECT sum(kwh) FROM leitura").fetchone()
    assert kwh == (40.0,)


@pytest.mark.skipif(not CSV.exists(), reason="dataset CU-BEMS nao baixado (data/publicos)")
def test_amostra_real_cu_bems_ate_relatorio(tmp_path: Path) -> None:
    con = conectar()
    inicio, fim = pd.Timestamp("2018-08-01"), pd.Timestamp("2018-09-01")  # mesmo mes do relatorio
    linhas = carregar_cu_bems(con, CSV, "cu_bems_2018Floor2", inicio, fim)
    assert linhas > 0
    esperado_pontos = 31 * 24 * 60
    por_equipamento = con.execute(
        "SELECT min(n), max(n) FROM (SELECT count(*) AS n FROM leitura GROUP BY equipamento_id)"
    ).fetchone()
    assert por_equipamento == (esperado_pontos, esperado_pontos)  # calendario completo

    texto = gerar_relatorio(
        con, "cu_bems_2018Floor2", "2018-08", carregar_tarifas(), carregar_config_equipamentos()
    )
    assert DISCLAIMER in texto
    assert "Top 5" in texto
    destino = escrever_relatorio(texto, tmp_path, "cu_bems_2018Floor2", "2018-08")
    assert destino.read_text(encoding="utf-8") == texto
