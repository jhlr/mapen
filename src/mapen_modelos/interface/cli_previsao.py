"""CLI do estudo de previsao: roda os previsores no subconjunto do CU-BEMS e grava `previsao.json`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_modelos.application.estudo_previsao import EstudoPrevisao, ParametrosPrevisao
from mapen_modelos.application.portas import Previsor
from mapen_modelos.application.treinar_e_avaliar import ConfigAvaliacao
from mapen_modelos.infrastructure.arquivos import escrever_texto
from mapen_modelos.infrastructure.previsor_ets import PrevisorETS
from mapen_modelos.infrastructure.previsor_lightgbm import PrevisorLightGBM
from mapen_modelos.infrastructure.previsor_ridge import PrevisorRidge
from mapen_modelos.infrastructure.previsores_simples import PrevisorBaselineSazonal, PrevisorNaiveSazonal
from mapen_modelos.infrastructure.serie_duckdb import SeriesHorariasDuckDB
from mapen_modelos.infrastructure.subconjunto import CSV_PADRAO, DUCKDB_PADRAO, SENSOR_PADRAO, abrir_subconjunto
from mapen_modelos.interface.artefatos_json import serializar
from mapen_modelos.interface.artefatos_previsao import montar_previsao_json, renderizar_relatorio

# Do mais simples ao mais complexo (desempate pre-registrado).
ORDEM_SIMPLICIDADE: tuple[str, ...] = (
    "seasonal_naive_24",
    "seasonal_naive_168",
    "baseline_sazonal",
    "ridge",
    "ets_24_tipo_dia",
    "lightgbm_lag24",
)


def previsores(ets: Previsor, lightgbm: Previsor) -> list[Previsor]:
    return [
        PrevisorNaiveSazonal(24),
        PrevisorNaiveSazonal(168),
        PrevisorBaselineSazonal(),
        PrevisorRidge(),
        ets,
        lightgbm,
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_PADRAO)
    parser.add_argument("--duckdb", type=Path, default=DUCKDB_PADRAO)
    parser.add_argument("--sensor-id", default=SENSOR_PADRAO)
    parser.add_argument("--inicio", default="2018-07-01")
    parser.add_argument("--fim-treino", default="2018-11-04")
    parser.add_argument("--fim-teste", default="2018-12-02")
    parser.add_argument("--limiar-z", type=float, default=4.0)
    parser.add_argument("--semente", type=int, default=20181104)
    parser.add_argument("--eventos-por-tipo", type=int, default=2)
    parser.add_argument("--saida", type=Path, default=RAIZ / "data" / "m3")
    args = parser.parse_args(argv)
    p = ParametrosPrevisao(
        args.sensor_id, pd.Timestamp(args.inicio), pd.Timestamp(args.fim_treino), pd.Timestamp(args.fim_teste),
        args.limiar_z, args.semente, args.eventos_por_tipo,
    )
    con = abrir_subconjunto(args.duckdb, args.csv, p.sensor_id, p.inicio, p.fim_teste)
    lgbm = PrevisorLightGBM()
    ets = PrevisorETS()
    estudo = EstudoPrevisao(SeriesHorariasDuckDB(con), previsores(ets, lgbm), ORDEM_SIMPLICIDADE, lgbm)
    resultado = estudo.executar(p, ConfigAvaliacao())
    if ets.ajustes_sem_convergencia:
        resultado.avisos.append(f"ETS: {ets.ajustes_sem_convergencia} ajuste(s) sem convergencia (parametros do ultimo iterado usados)")
    escrever_texto(args.saida / "previsao.json", serializar(montar_previsao_json(resultado)))
    escrever_texto(args.saida / "relatorio_previsao.md", renderizar_relatorio(resultado))
    print(args.saida / "previsao.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
