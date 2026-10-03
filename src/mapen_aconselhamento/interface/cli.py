"""CLI do M1: carrega um andar do CU-BEMS para um DuckDB em memoria e grava o relatorio mensal."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from mapen_aconselhamento.application.relatorio_mensal import FONTE_DADOS_PADRAO, GerarRelatorioMensal
from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_aconselhamento.infrastructure.cu_bems import carregar_cu_bems
from mapen_aconselhamento.infrastructure.duckdb_leituras import LeiturasDuckDB, conectar
from mapen_aconselhamento.infrastructure.equipamentos_yaml import carregar_config_equipamentos
from mapen_aconselhamento.infrastructure.relatorio_arquivo import escrever_relatorio
from mapen_aconselhamento.infrastructure.tarifa_csv import carregar_tarifas
from mapen_aconselhamento.interface.relatorio_markdown import renderizar_relatorio


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="CSV de andar do CU-BEMS")
    parser.add_argument("sensor_id", help="identificador do predio/andar, ex.: cu_bems_2018Floor2")
    parser.add_argument("mes", help="mes do relatorio, AAAA-MM")
    parser.add_argument("--saida", type=Path, default=RAIZ / "data" / "relatorios")
    parser.add_argument("--fonte-dados", default=FONTE_DADOS_PADRAO, help="texto da linha Dados do relatorio")
    args = parser.parse_args(argv)

    inicio = pd.Timestamp(f"{args.mes}-01")
    fim = inicio + pd.offsets.MonthBegin(1)
    con = conectar()
    carregar_cu_bems(con, args.csv, args.sensor_id, inicio, fim)
    relatorio = GerarRelatorioMensal(LeiturasDuckDB(con)).executar(
        args.sensor_id,
        args.mes,
        carregar_tarifas(),
        carregar_config_equipamentos(),
        fonte_dados=args.fonte_dados,
    )
    destino = escrever_relatorio(renderizar_relatorio(relatorio), args.saida, args.sensor_id, args.mes)
    print(destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
