"""Relatorio markdown do M3 (pt-BR). Todos os numeros vem do `ResultadoM3`."""

from __future__ import annotations

import numpy as np

from mapen_modelos.application.benchmark_sintetico import TaxasDetector
from mapen_modelos.application.detectar_anomalias import TIPO_LIGHTGBM, TIPO_ZSCORE
from mapen_modelos.application.executar_m3 import ResultadoM3
from mapen_modelos.application.treinar_e_avaliar import ResultadoTreino
from mapen_modelos.domain.baseline import SEMANAS_MINIMAS
from mapen_modelos.domain.comparacao import DESCRICAO_REGRA_CONTROLES, resumir_varredura
from mapen_modelos.domain.injecao import TIPOS

MAX_ALERTAS_LISTADOS = 15


def _pct(v: float) -> str:
    return "n/d" if np.isnan(v) else f"{100.0 * v:.1f}%"


def _mae_ponderado(treino: ResultadoTreino) -> tuple[float, float, int]:
    horas = np.array([m.horas_teste for m in treino.metricas.values()], dtype=float)
    base = np.array([m.mae_baseline for m in treino.metricas.values()])
    mod = np.array([m.mae_modelo for m in treino.metricas.values()])
    return float((base * horas).sum() / horas.sum()), float((mod * horas).sum() / horas.sum()), int(horas.sum())


def _secao_dados(r: ResultadoM3, minutos: int) -> list[str]:
    p, t = r.parametros, r.treino
    return [
        "## 1. Dados (subconjunto documentado)",
        "",
        f"- Fonte: CU-BEMS (dado real), sensor `{p.sensor_id}` (um andar), carregado pelo carregador do M1.",
        f"- Periodo total: {p.inicio:%Y-%m-%d} a {p.fim_teste:%Y-%m-%d} (exclusivo), 1 min, {minutos} linhas de minuto.",
        f"- Treino e walk-forward: {p.inicio:%Y-%m-%d} a {p.fim_treino:%Y-%m-%d} (exclusivo), {t.horas_calendario} horas.",
        f"- Periodo reservado (deteccao, benchmark, antes x depois): {p.fim_treino:%Y-%m-%d} a {p.fim_teste:%Y-%m-%d} (exclusivo).",
        f"- Equipamentos no andar: {len(t.horas_validas)}; modelados: {len(t.modelos)}; "
        f"sem carga (media de treino < 0.05 kW, fora dos modelos): {len(t.sem_carga)} ({', '.join(t.sem_carga) or '-'}).",
        "- Hora vale so com os 60 minutos presentes; senao e NaN (sem interpolacao).",
        "",
        "| Equipamento | Horas validas / calendario |",
        "|---|---|",
        *[f"| {eq} | {n} / {t.horas_calendario} |" for eq, n in t.horas_validas.items()],
        "",
    ]


def _secao_mae(r: ResultadoM3) -> list[str]:
    t = r.treino
    base, mod, horas = _mae_ponderado(t)
    ganho = np.array([(m.mae_baseline - m.mae_modelo) / m.mae_baseline for m in t.metricas.values()])
    vitorias = int(sum(m.mae_modelo < m.mae_baseline for m in t.metricas.values()))
    linhas = [
        "## 2. Walk-forward: MAE (kW) em dobras de teste",
        "",
        f"Janela expansiva: treino inicial {r.config.treino_inicial}, teste {r.config.teste} por dobra, {len(t.dobras)} dobras.",
        "",
        "| Dobra | Treino | Teste |",
        "|---|---|---|",
        *[
            f"| {k} | {d.treino_inicio:%Y-%m-%d} a {d.treino_fim:%Y-%m-%d} | {d.teste_inicio:%Y-%m-%d} a {d.teste_fim:%Y-%m-%d} |"
            for k, d in enumerate(t.dobras)
        ],
        "",
        f"MAE agregado (ponderado por horas, {horas} horas-equipamento de teste): baseline sazonal **{base:.4f} kW**, "
        f"LightGBM **{mod:.4f} kW**. LightGBM melhor em {vitorias} de {len(t.metricas)} equipamentos; "
        f"melhora relativa mediana por equipamento: {_pct(float(np.median(ganho)))}.",
        "",
        "| Equipamento | Horas de teste | MAE baseline | MAE LightGBM | Variacao |",
        "|---|---|---|---|---|",
    ]
    for eq, m in t.metricas.items():
        linhas.append(
            f"| {eq} | {m.horas_teste} | {m.mae_baseline:.4f} | {m.mae_modelo:.4f} | "
            f"{_pct((m.mae_baseline - m.mae_modelo) / m.mae_baseline)} |"
        )
    linhas += [
        "",
        "O LightGBM usa lag 1 h; o baseline sazonal nao. A comparacao e MAE de previsao de 1 passo para o LightGBM "
        "contra esperado por hora da semana para o baseline, nao a mesma tarefa de previsao de horizonte longo.",
        "",
    ]
    return linhas


def _secao_d7(r: ResultadoM3) -> list[str]:
    d = r.deteccao
    agg = d.d7_agregado
    linhas = ["## 3. Checagem D7 (SHAP: identidade de calendario x historico)", ""]
    if agg is None:
        return [*linhas, "Sem explicacao calculada.", ""]
    linhas += [
        f"Agregado (periodo reservado, {d.horas_avaliadas} horas-equipamento): calendario (hora, dia da semana, feriado) "
        f"**{_pct(agg.participacao_calendario)}**, lag/janela movel **{_pct(agg.participacao_historico)}** do |SHAP| total.",
        "",
        "| Feature | Participacao no |SHAP| |",
        "|---|---|",
        *[f"| {f} | {_pct(v)} |" for f, v in agg.participacao_por_feature.items()],
        "",
    ]
    linhas += [f"AVISO: {a}" for a in agg.avisos] or ["Nenhuma feature unica passa de 50% no agregado."]
    linhas += [
        "",
        "| Equipamento | Calendario | Lag/janela | Feature dominante (> 50%) |",
        "|---|---|---|---|",
    ]
    for eq, c in d.d7_por_equipamento.items():
        linhas.append(
            f"| {eq} | {_pct(c.participacao_calendario)} | {_pct(c.participacao_historico)} | {c.feature_dominante or '-'} |"
        )
    return [*linhas, ""]


def _secao_alertas(r: ResultadoM3) -> list[str]:
    d = r.deteccao
    z = [a for a in d.alertas if a.tipo == TIPO_ZSCORE]
    m = [a for a in d.alertas if a.tipo == TIPO_LIGHTGBM]
    linhas = [
        "## 4. Alertas em dado real: candidatos, nao corroborados",
        "",
        f"Periodo {d.inicio:%Y-%m-%d} a {d.fim:%Y-%m-%d}, limiar |z| >= {d.limiar}. "
        f"Alertas de z-score: {len(z)}; de LightGBM: {len(m)}; sobre {d.horas_avaliadas} horas-equipamento. "
        "Nao ha rotulo: nenhuma precisao ou recall e reportada. Nenhum alerta foi corroborado pelo cliente (0).",
        "",
        f"### Maiores alertas de z-score (ate {MAX_ALERTAS_LISTADOS})",
        "",
        "| Equipamento | Hora | z | Esperado kW | Observado kW | Janela do baseline | Baseline fraca |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in sorted(z, key=lambda x: -abs(x.z))[:MAX_ALERTAS_LISTADOS]:
        linhas.append(
            f"| {a.equipamento} | {a.ts:%Y-%m-%d %H:%M} | {a.z:.1f} | {a.esperado:.3f} | {a.observado:.3f} | "
            f"{a.janela_inicio:%Y-%m-%d} a {a.janela_fim:%Y-%m-%d} | {'sim' if a.baseline_fraca else 'nao'} |"
        )
    linhas += [
        "",
        f"### Maiores alertas de LightGBM (ate {MAX_ALERTAS_LISTADOS}), com as 3 principais features SHAP",
        "",
        "| Equipamento | Hora | z | Previsto kW | Observado kW | Top 3 SHAP |",
        "|---|---|---|---|---|---|",
    ]
    for a in sorted(m, key=lambda x: -abs(x.z))[:MAX_ALERTAS_LISTADOS]:
        top = ", ".join(f"{c.feature} ({c.shap:+.3f})" for c in (a.top_shap or []))
        linhas.append(
            f"| {a.equipamento} | {a.ts:%Y-%m-%d %H:%M} | {a.z:.1f} | {a.esperado:.3f} | {a.observado:.3f} | {top} |"
        )
    return [*linhas, ""]


def _linha_taxa(nome: str, t: TaxasDetector) -> str:
    por_tipo = " | ".join(
        f"{t.detectados.get(k, 0)}/{t.injetados.get(k, 0)} ({_pct(t.taxa_deteccao(k))})" for k in TIPOS
    )
    return (
        f"| {nome} | {por_tipo} | {t.detectados.get('pico', 0) + t.detectados.get('elevacao_fora_de_horario', 0) + t.detectados.get('ligado_continuo', 0)}"
        f"/{sum(t.injetados.values())} ({_pct(t.taxa_deteccao())}) | {t.alertas_fora}/{t.horas_fora} ({_pct(t.taxa_falso_alarme())}) |"
    )


def _secao_benchmark(r: ResultadoM3) -> list[str]:
    b = r.benchmark
    return [
        "## 5. Benchmark SINTETICO de injecao (nao e precisao/recall em dado real)",
        "",
        f"Anomalias conhecidas injetadas no periodo reservado ({b.inicio:%Y-%m-%d} a {b.fim:%Y-%m-%d}), semente {b.semente}, "
        f"{b.por_tipo} evento(s) de cada tipo por equipamento ({len(b.equipamentos)} equipamentos), limiar |z| >= {b.limiar}. "
        "Tipos: pico (1 h, +3 x P95), elevacao fora de horario (6 h de madrugada, +0.5 x P95), ligado continuo "
        "(12 h a partir das 20:00 presas no P95). Evento detectado = pelo menos 1 alerta do detector dentro da janela do evento. "
        "Falso alarme = alertas por hora fora dos eventos e fora da zona que o historico (lag 1/24/168, janela 24 h) enxerga do evento. "
        "Como a serie base e real, o falso alarme inclui anomalias reais nao rotuladas: e limite superior.",
        "",
        "| Detector | Pico | Elevacao fora de horario | Ligado continuo | Total | Falso alarme (horas) |",
        "|---|---|---|---|---|---|",
        _linha_taxa("z-score sazonal", b.taxas[TIPO_ZSCORE]),
        _linha_taxa("LightGBM (residuo)", b.taxas[TIPO_LIGHTGBM]),
        "",
    ]


def _secao_economia(r: ResultadoM3) -> list[str]:
    ad = r.antes_depois
    red = ad.reducao
    assert red is not None
    ctrl = [c.economia_pct for e, c in r.controle.por_equipamento.items()]
    ctrl_abs = np.abs(np.array(ctrl, dtype=float))
    fracos = [e for e, c in ad.por_equipamento.items() if c.baseline_fraca]
    c = ad.por_equipamento[red.equipamento]
    alvo = 100.0 * red.fracao
    v_base = resumir_varredura(r.varredura.baseline_pct, alvo, ad.tolerancia_pp)
    v_ctrl = resumir_varredura(r.varredura.controle_pct, alvo, ad.tolerancia_pp)
    cc = ad.por_equipamento_controle[red.equipamento]
    linhas = [
        "## 6. Antes x depois com baseline normalizado (validacao de METODO)",
        "",
        "Nao existe intervencao real nos dados publicos. Uma reducao sintetica conhecida foi aplicada ao periodo "
        "\"depois\" para checar se o metodo a recupera. **Isto valida o metodo, nao e economia real.**",
        "",
        f"- Antes: {ad.inicio_antes:%Y-%m-%d} a {ad.fim_antes:%Y-%m-%d}; depois: {ad.fim_antes:%Y-%m-%d} a {ad.fim_depois:%Y-%m-%d}.",
        f"- Reducao sintetica: {100 * red.fracao:.0f}% em `{red.equipamento}` a partir de {red.a_partir_de:%Y-%m-%d}.",
        f"- Recuperado: **{ad.recuperado_pct:.2f}%** (tolerancia +-{ad.tolerancia_pp} pp): "
        f"{'dentro' if ad.dentro_da_tolerancia else 'FORA'} da tolerancia.",
        f"- `{red.equipamento}`: antes {c.kwh_antes:.1f} kWh, depois {c.kwh_depois:.1f} kWh, contrafactual {c.kwh_contrafactual:.1f} kWh, "
        f"fator de nivel {c.fator_nivel:.3f}, economia {c.economia_kwh:.1f} kWh.",
        f"- Varredura (baseline normalizado): a mesma reducao de {alvo:.0f}% aplicada, uma por vez, a cada um dos {v_base.avaliados} "
        f"equipamentos modelados: {v_base.dentro_da_tolerancia} de {v_base.avaliados} recuperam dentro de +-{ad.tolerancia_pp} pp; "
        f"erro absoluto mediano {v_base.erro_abs_mediano_pp:.2f} pp, maximo {v_base.erro_abs_maximo_pp:.2f} pp. A deriva semanal real "
        "de nivel (ocupacao, calendario letivo) nao e normalizada pelo baseline sazonal.",
        f"- Com grupo-controle (diferenca em diferencas; controles = {DESCRICAO_REGRA_CONTROLES}): alvo `{red.equipamento}` recupera "
        f"**{ad.recuperado_controle_pct:.2f}%** com controles {', '.join(cc.controles) or 'nenhum'}: "
        f"{'dentro' if ad.dentro_da_tolerancia_controle else 'FORA'} da tolerancia. Varredura: {v_ctrl.dentro_da_tolerancia} de "
        f"{v_ctrl.avaliados} dentro de +-{ad.tolerancia_pp} pp; erro absoluto mediano {v_ctrl.erro_abs_mediano_pp:.2f} pp, "
        f"maximo {v_ctrl.erro_abs_maximo_pp:.2f} pp; sem controle valido: {', '.join(v_ctrl.sem_resultado) or 'nenhum'}.",
        f"- Controle (sem reducao): economia espuria por equipamento, |media| {ctrl_abs.mean():.2f}%, maximo {ctrl_abs.max():.2f}%.",
        f"- Baseline fraca (menos de {SEMANAS_MINIMAS} semanas completas): "
        f"{', '.join(fracos) if fracos else 'nenhum equipamento'}. Semanas completas no treino: "
        f"{next(iter(r.treino.modelos.values())).baseline.semanas_completas}.",
        "",
        "| Equipamento | kWh antes | kWh depois | Economia % (com reducao no alvo) | Economia % (controle) | Recuperado % baseline (reducao so neste equipamento) | Recuperado % grupo-controle | Controles | Baseline fraca |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for eq, x in ad.por_equipamento.items():
        k = r.controle.por_equipamento[eq]
        linhas.append(
            f"| {eq} | {x.kwh_antes:.1f} | {x.kwh_depois:.1f} | {x.economia_pct:.2f} | {k.economia_pct:.2f} | "
            f"{r.varredura.baseline_pct[eq]:.2f} | {r.varredura.controle_pct[eq]:.2f} | "
            f"{', '.join(r.varredura.controles[eq]) or 'sem controle valido'} | {'sim' if x.baseline_fraca else 'nao'} |"
        )
    return [*linhas, ""]


def renderizar_relatorio(r: ResultadoM3, minutos_carregados: int) -> str:
    cabecalho = [
        f"# M3: baseline, anomalia e economia ({r.parametros.sensor_id})",
        "",
        "Dado real do CU-BEMS; sem rotulos e sem intervencao real. Metricas de deteccao so existem no benchmark "
        "sintetico; alertas reais sao candidatos nao corroborados.",
        "",
    ]
    return "\n".join(
        [
            *cabecalho,
            *_secao_dados(r, minutos_carregados),
            *_secao_mae(r),
            *_secao_d7(r),
            *_secao_alertas(r),
            *_secao_benchmark(r),
            *_secao_economia(r),
        ]
    )
