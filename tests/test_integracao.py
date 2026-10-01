from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mapen_aconselhamento.ingest import carregar_cu_bems, conectar
from mapen_aconselhamento.recomenda import ConfigEquipamentos
from mapen_aconselhamento.relatorio import DISCLAIMER, escrever_relatorio, gerar_relatorio
from mapen_aconselhamento.tarifa import RAIZ, Tarifas

CSV = RAIZ / "data" / "publicos" / "cu_bems" / "2018Floor2.csv"


@pytest.mark.skipif(not CSV.exists(), reason="dataset CU-BEMS nao baixado (data/publicos)")
def test_amostra_real_cu_bems_ate_relatorio(tmp_path: Path) -> None:
    con = conectar()
    inicio, fim = pd.Timestamp("2018-08-06"), pd.Timestamp("2018-08-13")  # 1 semana, seg-dom
    linhas = carregar_cu_bems(con, CSV, "cu_bems_2018Floor2", inicio, fim)
    assert linhas > 0
    esperado_pontos = 7 * 24 * 60
    por_equipamento = con.execute(
        "SELECT min(n), max(n) FROM (SELECT count(*) AS n FROM leitura GROUP BY equipamento_id)"
    ).fetchone()
    assert por_equipamento == (esperado_pontos, esperado_pontos)  # calendario completo

    texto = gerar_relatorio(
        con, "cu_bems_2018Floor2", "2018-08", Tarifas.carregar(), ConfigEquipamentos.carregar()
    )
    assert DISCLAIMER in texto
    assert "Top 5" in texto
    destino = escrever_relatorio(texto, tmp_path, "cu_bems_2018Floor2", "2018-08")
    assert destino.read_text(encoding="utf-8") == texto


def test_bdg2_le_direto_do_zip(tmp_path: Path) -> None:
    import zipfile

    from mapen_aconselhamento.ingest import BDG2_ELETRICIDADE, carregar_bdg2

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
