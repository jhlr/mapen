"""Renderizacao do relatorio mensal em markdown."""

from __future__ import annotations

from mapen_aconselhamento.application.relatorio_mensal import RelatorioMensal
from mapen_aconselhamento.domain.equipamentos import ALTA, BAIXA, CENTRAL
from mapen_aconselhamento.domain.tarifa import Tarifas

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


def descrever_valores(tarifas: Tarifas) -> str:
    """Texto para o relatorio: o que os valores incluem."""
    if tarifas.gross_up is None and tarifas.bandeira_rs_kwh is None:
        return "SEM tributos e SEM bandeira (tarifa base homologada)"
    partes = []
    partes.append(
        "sem bandeira"
        if tarifas.bandeira_rs_kwh is None
        else f"com bandeira de R$ {tarifas.bandeira_rs_kwh:.5f}/kWh somada a todos os postos (hipotese)"
    )
    partes.append(
        "sem tributos"
        if tarifas.gross_up is None
        else f"com gross-up multiplicativo de {tarifas.gross_up:.4f} (tributos, informado, nao conferido)"
    )
    return ", ".join(partes)


def renderizar_relatorio(relatorio: RelatorioMensal) -> str:
    sensor_id, mes, n = relatorio.sensor_id, relatorio.mes, relatorio.n
    tarifas = relatorio.tarifas
    recs = relatorio.recomendacoes[CENTRAL]
    indice = {
        c: {(r.equipamento_id, r.faixa_origem): r for r in lista}
        for c, lista in relatorio.recomendacoes.items()
    }
    rotulo = {c: _pct(relatorio.fracoes(c)) for c in relatorio.recomendacoes}
    total = {c: relatorio.economia_total(c) for c in relatorio.recomendacoes}
    duplicados = relatorio.duplicados
    texto_duplicados = (
        "sem registro de carga"
        if duplicados is None
        else f"{duplicados[0]} descartados (politica `{duplicados[1]}`)"
    )
    vigencia = (
        "sem vigencia registrada"
        if tarifas.vigencia is None
        else f"vigencia {tarifas.vigencia[0]} a {tarifas.vigencia[1]}"
    )
    postos_21h = "intermediario" if tarifas.hora_21_intermediaria else "fora de ponta"
    valores = descrever_valores(tarifas)

    linhas = [
        f"# Relatorio de custo de energia: {sensor_id}, {mes}",
        "",
        f"> **Aviso:** {DISCLAIMER}",
        "",
        f"- Dados: {relatorio.fonte_dados}.",
        f"- Tarifa: {FONTE_TARIFA}, {vigencia}.",
        f"- Valores: {valores}.",
        f"- Pontos ausentes (sem interpolacao, fora do custo): {relatorio.ausentes} de {relatorio.pontos} "
        f"({relatorio.pct_ausente:.1f}%). "
        "Com lacunas, os custos abaixo sao um piso.",
        f"- Timestamps duplicados: {texto_duplicados}.",
        f"- Custo total, convencional: R$ {relatorio.custo_convencional_rs:.2f}.",
        f"- Custo total, branca: R$ {relatorio.custo_branca_rs:.2f}.",
        "",
        f"## Top {n} equipamentos por custo (convencional)",
        "",
        "| # | Equipamento | kWh | Custo convencional (R$) | Custo branca (R$) | Flexivel | % ausente |",
        "|---|---|---|---|---|---|---|",
    ]
    for pos, linha in enumerate(relatorio.ranking, start=1):
        flex = "sim" if linha.flexivel else "nao"
        linhas.append(
            f"| {pos} | {linha.equipamento_id} | {linha.kwh:.1f} | {linha.custo_convencional_rs:.2f} | "
            f"{linha.custo_branca_rs:.2f} | {flex} | {linha.pct_ausente:.1f}% |"
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
        f"1. Valores monetarios: {valores}.",
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
