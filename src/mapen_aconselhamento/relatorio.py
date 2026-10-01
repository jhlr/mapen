"""Relatorio markdown por predio/mes."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from mapen_aconselhamento.custo import custo_por_faixa, custo_total
from mapen_aconselhamento.ingest import ler_leituras
from mapen_aconselhamento.ranking import top_n
from mapen_aconselhamento.recomenda import ConfigEquipamentos, recomendar
from mapen_aconselhamento.tarifa import BRANCA, CONVENCIONAL, Tarifas

DISCLAIMER = (
    "Curva de carga estrangeira + tarifa brasileira = demonstracao de metodo. "
    "Este relatorio nao mostra o comportamento de carga no Brasil e nao e aconselhamento a cliente."
)
FONTE_TARIFA = "Neoenergia PE, REH 3.583/2026, subgrupo B3, sem tributos e sem bandeira"


def gerar_relatorio(
    con: duckdb.DuckDBPyConnection,
    sensor_id: str,
    mes: str,
    tarifas: Tarifas,
    config: ConfigEquipamentos,
    n: int = 5,
    fonte_dados: str = "dataset publico (ver docs/datasets_publicos.md)",
) -> str:
    """Relatorio do predio `sensor_id` no mes `mes` (formato AAAA-MM)."""
    inicio = pd.Timestamp(f"{mes}-01")
    fim = inicio + pd.offsets.MonthBegin(1)
    leituras = ler_leituras(con, sensor_id, inicio, fim)
    if leituras.empty:
        raise ValueError(f"sem leituras para {sensor_id} em {mes}")

    ausentes = int(leituras["ausente"].sum())
    pct = 100.0 * ausentes / len(leituras)
    conv = custo_por_faixa(leituras, tarifas, CONVENCIONAL)
    branca = custo_por_faixa(leituras, tarifas, BRANCA)
    rank_conv = top_n(conv, n)
    custo_branca = branca.groupby("equipamento_id")["custo_rs"].sum()
    recs = recomendar(branca, tarifas, config)

    linhas = [
        f"# Relatorio de custo de energia: {sensor_id}, {mes}",
        "",
        f"> **Aviso:** {DISCLAIMER}",
        "",
        f"- Dados: {fonte_dados}.",
        f"- Tarifa: {FONTE_TARIFA}.",
        f"- Pontos ausentes (sem interpolacao, fora do custo): {ausentes} de {len(leituras)} ({pct:.1f}%). "
        "Com lacunas, os custos abaixo sao um piso.",
        f"- Custo total, convencional: R$ {custo_total(conv):.2f}.",
        f"- Custo total, branca: R$ {custo_total(branca):.2f}.",
        "",
        f"## Top {n} equipamentos por custo (convencional)",
        "",
        "| # | Equipamento | kWh | Custo convencional (R$) | Custo branca (R$) | Flexivel |",
        "|---|---|---|---|---|---|",
    ]
    for pos, linha in enumerate(rank_conv.itertuples(index=False), start=1):
        eq = str(linha.equipamento_id)
        flex = "sim" if config.para(eq).flexivel else "nao"
        linhas.append(
            f"| {pos} | {eq} | {linha.kwh:.1f} | {linha.custo_rs:.2f} | "
            f"{float(custo_branca.get(eq, 0.0)):.2f} | {flex} |"
        )
    linhas += [
        "",
        "## Recomendacoes: mover carga flexivel (tarifa branca)",
        "",
        "Economia = kWh movido x (preco da faixa de origem - preco da faixa de destino). "
        "O kWh movido e a fracao do cenario em `config/equipamentos.yaml` (hipotese, nao medicao). "
        "Cargas nao marcadas `flexivel` nao tem economia calculada.",
        "",
    ]
    if recs:
        linhas += [
            "| Equipamento | De | Para | kWh movido | Economia no mes (R$) |",
            "|---|---|---|---|---|",
        ]
        for r in recs:
            linhas.append(
                f"| {r.equipamento_id} | {r.faixa_origem} | {r.faixa_destino} | "
                f"{r.kwh_movido:.2f} | {r.economia_rs:.2f} |"
            )
    else:
        linhas.append("Nenhuma carga flexivel com consumo em faixa mais cara neste mes.")
    linhas.append("")
    return "\n".join(linhas)


def escrever_relatorio(texto: str, diretorio: Path, sensor_id: str, mes: str) -> Path:
    """Grava o relatorio em `diretorio/<sensor_id>_<mes>.md`."""
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / f"{sensor_id}_{mes}.md"
    destino.write_text(texto, encoding="utf-8")
    return destino
