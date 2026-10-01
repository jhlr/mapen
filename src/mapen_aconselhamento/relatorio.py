"""Relatorio markdown por predio/mes."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from mapen_aconselhamento.custo import custo_por_faixa, custo_total
from mapen_aconselhamento.ingest import ler_duplicados, ler_leituras
from mapen_aconselhamento.ranking import pct_ausente_por_equipamento, top_n
from mapen_aconselhamento.recomenda import (
    ALTA,
    BAIXA,
    CENTRAL,
    ConfigEquipamentos,
    Recomendacao,
    recomendar,
)
from mapen_aconselhamento.tarifa import BRANCA, CONVENCIONAL, Tarifas

DISCLAIMER = (
    "Curva de carga estrangeira + tarifa brasileira = demonstracao de metodo. "
    "Este relatorio nao mostra o comportamento de carga no Brasil e nao e aconselhamento a cliente."
)
FONTE_TARIFA = "Neoenergia PE, REH 3.583/2026, subgrupo B3"
CAVEAT_FRACAO = (
    "A fracao movivel (faixa 10-25%, central 18%) vem de estudos de predios de escritorio nos EUA "
    "(LBNL 2006, via docs/m1_premissas.md), nao de medicao brasileira; nao validada para clima "
    "tropical nem splits. A economia e hipotese de cenario, nao resultado."
)
CAVEAT_TIMESTAMPS = (
    "Timestamps ingenuos (sem fuso): horario de verao nao e tratado. Hora repetida vira "
    "timestamp duplicado e hora pulada vira lacuna."
)


def _pct(fracoes: list[float]) -> str:
    """Rotulo de percentual: '18%' ou '10%/12%' se as regras divergem."""
    return "/".join(f"{100 * f:g}%" for f in sorted(set(fracoes)))


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
    duplicados = ler_duplicados(con, sensor_id)
    texto_duplicados = (
        "sem registro de carga"
        if duplicados is None
        else f"{duplicados[0]} descartados (politica `{duplicados[1]}`)"
    )
    conv = custo_por_faixa(leituras, tarifas, CONVENCIONAL)
    branca = custo_por_faixa(leituras, tarifas, BRANCA)
    rank_conv = top_n(conv, pct_ausente_por_equipamento(leituras), n)
    custo_branca = branca.groupby("equipamento_id")["custo_rs"].sum()
    por_cenario = {c: recomendar(branca, tarifas, config, cenario=c) for c in (BAIXA, CENTRAL, ALTA)}
    recs = por_cenario[CENTRAL]
    indice: dict[str, dict[tuple[str, str], Recomendacao]] = {
        c: {(r.equipamento_id, r.faixa_origem): r for r in lista} for c, lista in por_cenario.items()
    }
    rotulo = {c: _pct([r.fracao_movivel for r in lista]) for c, lista in por_cenario.items()}
    total = {c: sum(r.economia_rs for r in lista) for c, lista in por_cenario.items()}
    vigencia = (
        "sem vigencia registrada"
        if tarifas.vigencia is None
        else f"vigencia {tarifas.vigencia[0]} a {tarifas.vigencia[1]}"
    )
    postos_21h = "intermediario" if tarifas.hora_21_intermediaria else "fora de ponta"

    linhas = [
        f"# Relatorio de custo de energia: {sensor_id}, {mes}",
        "",
        f"> **Aviso:** {DISCLAIMER}",
        "",
        f"- Dados: {fonte_dados}.",
        f"- Tarifa: {FONTE_TARIFA}, {vigencia}.",
        f"- Valores: {tarifas.descricao_valores()}.",
        f"- Pontos ausentes (sem interpolacao, fora do custo): {ausentes} de {len(leituras)} ({pct:.1f}%). "
        "Com lacunas, os custos abaixo sao um piso.",
        f"- Timestamps duplicados: {texto_duplicados}.",
        f"- Custo total, convencional: R$ {custo_total(conv):.2f}.",
        f"- Custo total, branca: R$ {custo_total(branca):.2f}.",
        "",
        f"## Top {n} equipamentos por custo (convencional)",
        "",
        "| # | Equipamento | kWh | Custo convencional (R$) | Custo branca (R$) | Flexivel | % ausente |",
        "|---|---|---|---|---|---|---|",
    ]
    for pos, linha in enumerate(rank_conv.itertuples(index=False), start=1):
        eq = str(linha.equipamento_id)
        flex = "sim" if config.para(eq).flexivel else "nao"
        linhas.append(
            f"| {pos} | {eq} | {linha.kwh:.1f} | {linha.custo_rs:.2f} | "
            f"{float(custo_branca.get(eq, 0.0)):.2f} | {flex} | {linha.pct_ausente:.1f}% |"
        )
    linhas += [
        "",
        "## Recomendacoes: mover carga flexivel (tarifa branca)",
        "",
        "Economia = kWh movido x (preco da faixa de origem - preco da faixa de destino). "
        "O kWh movido e a fracao do cenario em `config/equipamentos.yaml` (hipotese, nao medicao). "
        "Cargas nao marcadas `flexivel` nao tem economia calculada.",
        "",
        f"Economia total no mes sob hipotese de {rotulo[BAIXA]} movel: R$ {total[BAIXA]:.2f}; "
        f"de {rotulo[CENTRAL]} movel: R$ {total[CENTRAL]:.2f}; "
        f"de {rotulo[ALTA]} movel: R$ {total[ALTA]:.2f}.",
        "",
    ]
    if recs:
        linhas += [
            "| Equipamento | De | Para | kWh movido (central) | "
            f"Economia sob hipotese de {rotulo[BAIXA]} movel (R$) | "
            f"Economia sob hipotese de {rotulo[CENTRAL]} movel (R$) | "
            f"Economia sob hipotese de {rotulo[ALTA]} movel (R$) |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in recs:
            chave = (r.equipamento_id, r.faixa_origem)
            linhas.append(
                f"| {r.equipamento_id} | {r.faixa_origem} | {r.faixa_destino} | "
                f"{r.kwh_movido:.2f} | {indice[BAIXA][chave].economia_rs:.2f} | "
                f"{r.economia_rs:.2f} | {indice[ALTA][chave].economia_rs:.2f} |"
            )
    else:
        linhas.append("Nenhuma carga flexivel com consumo em faixa mais cara neste mes.")
    linhas += [
        "",
        "## Ressalvas",
        "",
        f"1. Valores monetarios: {tarifas.descricao_valores()}.",
        f"2. Hora 21:00 (dias uteis): tratada como {postos_21h}. Nao confirmada para a Neoenergia PE "
        "(fontes em conflito, docs/m1_premissas.md secao 1); o padrao e fora de ponta.",
        "3. Feriados: os 11 nacionais da lista de docs/m1_premissas.md (1/jan, 21/abr, 1/mai, 7/set, "
        "12/out, 2/nov, 15/nov, 25/dez, terca de carnaval, sexta-feira da Paixao, Corpus Christi) "
        "e fins de semana sao fora de ponta. 20/nov nao esta na lista e nao e modelado; a lista vem de "
        "resumo de busca da REN 1.000/2021 (texto primario nao lido).",
        f"4. {CAVEAT_FRACAO}",
        f"5. {CAVEAT_TIMESTAMPS}",
        "",
    ]
    return "\n".join(linhas)


def escrever_relatorio(texto: str, diretorio: Path, sensor_id: str, mes: str) -> Path:
    """Grava o relatorio em `diretorio/<sensor_id>_<mes>.md`."""
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / f"{sensor_id}_{mes}.md"
    destino.write_text(texto, encoding="utf-8")
    return destino
