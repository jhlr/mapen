"""Artefatos do estudo de previsao: `previsao.json` e relatorio markdown (esquema em docs/m3_notas.md)."""

from __future__ import annotations

import math

import pandas as pd

from mapen_modelos.application.estudo_previsao import ResultadoPrevisao
from mapen_modelos.domain.metricas_previsao import NAIVE_168, mediana
from mapen_modelos.domain.previsao import DEFASAGEM_MINIMA_H, HORIZONTE_H

VERSAO_ESQUEMA = 1
AVISO = (
    "Estudo de previsao do dia seguinte (origem = meia-noite, defasagem minima 24 h) em CU-BEMS Floor2. "
    "O benchmark e SINTETICO: nao ha rotulo real."
)


def _n(v: float, casas: int = 4) -> float | None:
    return None if math.isnan(v) else round(v, casas)


def _ts(t: pd.Timestamp) -> str:
    return t.isoformat()


def montar_previsao_json(r: ResultadoPrevisao) -> dict[str, object]:
    p = r.parametros
    mase = r.mase_reservado()
    d = r.decisao
    metricas = {
        m: {
            e: {"mae_kw": _n(x.mae), "rmse_kw": _n(x.rmse), "mase": _n(x.mase), "horas": x.horas}
            for e, x in por_eq.items()
        }
        for m, por_eq in r.reservado.items()
    }
    saida: dict[str, object] = {
        "versao_esquema": VERSAO_ESQUEMA,
        "sensor_id": p.sensor_id,
        "natureza": "estudo_previsao_dia_seguinte",
        "aviso": AVISO,
        "protocolo": {
            "origem": "meia-noite",
            "horizonte_h": HORIZONTE_H,
            "defasagem_minima_h": DEFASAGEM_MINIMA_H,
            "treino": {"inicio": _ts(p.inicio), "fim": _ts(p.fim_treino)},
            "reservado": {"inicio": _ts(p.fim_treino), "fim": _ts(p.fim_teste)},
            "dobras_walk_forward": len(r.dobras),
            "referencia_mase": NAIVE_168,
        },
        "equipamentos": r.equipamentos,
        "sem_carga": r.sem_carga,
        "modelos": r.modelos,
        "metricas_reservado": metricas,
        "mae_agregado_kw": {m: _n(v) for m, v in r.mae_agregado.items()},
        "mediana_mase_reservado": {m: _n(v) for m, v in d.medianas.items()},
        "mediana_mase_desenvolvimento": {m: _n(mediana(v)) for m, v in r.desenvolvimento.items()},
        "vitorias_vs_naive168": d.vitorias_vs_naive168,
        "vitorias_melhor_de_todos": d.vitorias_melhor_de_todos,
        "decisao": {
            "regra_aplicada": d.regra_aplicada,
            "adotado": d.adotado,
            "passaram_regra_de_ganho": d.passaram,
            "melhor_mediana": d.melhor_mediana,
            "motivo": d.motivo,
        },
        "mase_por_equipamento": {m: {e: _n(v) for e, v in por_eq.items()} for m, por_eq in mase.items()},
        "avisos": r.avisos,
        "shap_lightgbm": None,
        "benchmark_sintetico": None,
    }
    if r.shap is not None:
        s = r.shap
        saida["shap_lightgbm"] = {
            "participacao_por_feature": {f: _n(v) for f, v in s.participacao_por_feature.items()},
            "participacao_por_grupo": {g: _n(v) for g, v in s.participacao_por_grupo.items()},
            "d7_feature_dominante": s.feature_dominante,
            "d7_flag": s.feature_dominante is not None,
            "equipamentos_com_flag": s.equipamentos_com_flag,
            "horas": s.horas,
        }
    if r.benchmark is not None:
        b = r.benchmark
        t = b.taxas
        saida["benchmark_sintetico"] = {
            "sintetico": True,
            "previsor": b.previsor,
            "semente": b.semente,
            "eventos_por_tipo_por_equipamento": b.por_tipo,
            "limiar_z": b.limiar,
            "injetados": t.injetados,
            "detectados": t.detectados,
            "taxa_deteccao": _n(t.taxa_deteccao()),
            "taxa_deteccao_por_tipo": {k: _n(t.taxa_deteccao(k)) for k in t.injetados},
            "alertas_fora_da_zona": t.alertas_fora,
            "horas_fora_da_zona": t.horas_fora,
            "taxa_falso_alarme": _n(t.taxa_falso_alarme()),
        }
    return saida


def renderizar_relatorio(r: ResultadoPrevisao) -> str:
    d = r.decisao
    linhas = ["# Estudo de previsao (dia seguinte), MASE no periodo reservado", ""]
    linhas.append("| Modelo | MAE kW (agregado) | Mediana MASE | Mediana MASE (dobras) | Vitorias vs naive-168 | Melhor em |")
    linhas.append("|---|---|---|---|---|---|")
    for m in r.modelos:
        vit = "-" if m == NAIVE_168 else f"{d.vitorias_vs_naive168[m]}/{len(r.equipamentos)}"
        linhas.append(
            f"| {m} | {r.mae_agregado[m]:.4f} | {d.medianas[m]:.4f} | {mediana(r.desenvolvimento[m]):.4f} "
            f"| {vit} | {d.vitorias_melhor_de_todos[m]} |"
        )
    linhas += ["", f"Decisao: {d.motivo}", "", "## Por equipamento (MAE kW / RMSE kW / MASE, reservado)", ""]
    linhas.append("| Equipamento | " + " | ".join(r.modelos) + " |")
    linhas.append("|---|" + "---|" * len(r.modelos))
    for e in r.equipamentos:
        celulas = [
            f"{r.reservado[m][e].mae:.3f} / {r.reservado[m][e].rmse:.3f} / {r.reservado[m][e].mase:.3f}"
            for m in r.modelos
        ]
        linhas.append(f"| {e} | " + " | ".join(celulas) + " |")
    if r.shap is not None:
        s = r.shap
        linhas += ["", "## SHAP do LightGBM de previsao", ""]
        linhas.append("Grupos: " + ", ".join(f"{g} {v:.1%}" for g, v in s.participacao_por_grupo.items()))
        linhas.append("Features: " + ", ".join(f"{f} {v:.1%}" for f, v in s.participacao_por_feature.items()))
        linhas.append(f"D7 (feature unica > 50%): {s.feature_dominante or 'nao dispara'}; equipamentos com flag: {s.equipamentos_com_flag or 'nenhum'}")
    if r.benchmark is not None:
        b = r.benchmark
        t = b.taxas
        linhas += ["", f"## Benchmark SINTETICO ({b.previsor})", ""]
        for tipo in t.injetados:
            linhas.append(f"- {tipo}: {t.detectados.get(tipo, 0)}/{t.injetados[tipo]} ({t.taxa_deteccao(tipo):.1%})")
        linhas.append(f"- total: {sum(t.detectados.values())}/{sum(t.injetados.values())} ({t.taxa_deteccao():.1%})")
        linhas.append(f"- falso alarme: {t.alertas_fora}/{t.horas_fora} ({t.taxa_falso_alarme():.2%})")
    return "\n".join(linhas) + "\n"
