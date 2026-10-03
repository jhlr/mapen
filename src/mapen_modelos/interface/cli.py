"""CLI do M3: carrega o subconjunto do CU-BEMS, roda o ciclo completo e grava relatorio e JSONs."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_modelos.application.executar_m3 import ExecutarM3, ParametrosM3, ResultadoM3
from mapen_modelos.application.resumo_m3 import FonteDados
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao
from mapen_modelos.infrastructure.arquivos import escrever_texto
from mapen_modelos.infrastructure.lightgbm_modelo import TreinadorLightGBM
from mapen_modelos.infrastructure.serie_duckdb import SeriesHorariasDuckDB
from mapen_modelos.infrastructure.shap_explicador import ExplicadorShap
from mapen_modelos.infrastructure.subconjunto import CSV_PADRAO, DUCKDB_PADRAO, SENSOR_PADRAO, abrir_subconjunto
from mapen_modelos.interface.artefatos_json import montar_alertas, montar_economia, montar_resumo_json, serializar
from mapen_modelos.interface.relatorio_markdown import renderizar_relatorio

# 22 semanas exatas a partir de domingo 2018-07-01: 18 de treino/walk-forward, 4 reservadas.
INICIO_PADRAO = "2018-07-01"
FIM_TREINO_PADRAO = "2018-11-04"
FIM_TESTE_PADRAO = "2018-12-02"
MEIO_TESTE_PADRAO = "2018-11-18"


def publicar(m3: ExecutarM3, resultado: ResultadoM3, fonte: FonteDados, saida: Path) -> None:
    """Grava tudo que o M3 publica: relatorio markdown e os tres JSON lidos pela API."""
    escrever_texto(saida / "relatorio_m3.md", renderizar_relatorio(resultado, fonte.linhas_minuto))
    escrever_texto(saida / "resumo.json", serializar(montar_resumo_json(m3.resumir(resultado, fonte))))
    escrever_texto(saida / "alertas.json", serializar(montar_alertas(resultado)))
    escrever_texto(saida / "economia.json", serializar(montar_economia(resultado)))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_PADRAO)
    parser.add_argument("--duckdb", type=Path, default=DUCKDB_PADRAO)
    parser.add_argument("--sensor-id", default=SENSOR_PADRAO)
    parser.add_argument("--inicio", default=INICIO_PADRAO)
    parser.add_argument("--fim-treino", default=FIM_TREINO_PADRAO)
    parser.add_argument("--meio-teste", default=MEIO_TESTE_PADRAO)
    parser.add_argument("--fim-teste", default=FIM_TESTE_PADRAO)
    parser.add_argument("--limiar-z", type=float, default=4.0)
    parser.add_argument("--semente", type=int, default=20181104)
    parser.add_argument("--eventos-por-tipo", type=int, default=2)
    parser.add_argument("--equipamento-reducao", default="z1_Light")
    parser.add_argument("--reducao", type=float, default=0.15)
    parser.add_argument("--saida", type=Path, default=RAIZ / "data" / "m3")
    args = parser.parse_args(argv)

    p = ParametrosM3(
        sensor_id=args.sensor_id,
        inicio=pd.Timestamp(args.inicio),
        fim_treino=pd.Timestamp(args.fim_treino),
        fim_teste=pd.Timestamp(args.fim_teste),
        limiar_z=args.limiar_z,
        semente=args.semente,
        eventos_por_tipo=args.eventos_por_tipo,
        equipamento_reducao=args.equipamento_reducao,
        fracao_reducao=args.reducao,
        meio_do_teste=pd.Timestamp(args.meio_teste),
    )
    con = abrir_subconjunto(args.duckdb, args.csv, p.sensor_id, p.inicio, p.fim_teste)
    linha = con.execute("SELECT count(*) FROM leitura WHERE sensor_id = ?", [p.sensor_id]).fetchone()
    minutos = int(linha[0]) if linha is not None else 0
    m3 = ExecutarM3(SeriesHorariasDuckDB(con), TreinadorLightGBM(), ExplicadorShap())
    resultado = m3.executar(p, ConfigAvaliacao())
    fonte = FonteDados(f"CU-BEMS (dado real), {p.sensor_id.removeprefix('cu_bems_')}", minutos)
    publicar(m3, resultado, fonte, args.saida)
    print(args.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
