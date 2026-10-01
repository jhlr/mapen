"""Artefatos JSON do M3 para o dashboard: `resumo.json`, `alertas.json` e `economia.json`.

Esquemas documentados em docs/m3_notas.md. Os alertas sao candidatos nao corroborados (sem
rotulo real); a economia e validacao de metodo com reducao sintetica, nao economia real.
"""

from __future__ import annotations

import json
import math

import pandas as pd

from mapen_modelos.application.detectar_anomalias import STATUS_CANDIDATO, Alerta
from mapen_modelos.application.executar_m3 import ResultadoM3
from mapen_modelos.application.resumo_m3 import JanelaResumo, ResumoM3

VERSAO_ESQUEMA = 1


def _num(v: float) -> float | None:
    return None if math.isnan(v) else v


def _ts(t: pd.Timestamp) -> str:
    return t.isoformat()


def _alerta(a: Alerta) -> dict[str, object]:
    return {
        "equipamento": a.equipamento,
        "timestamp": _ts(a.ts),
        "tipo": a.tipo,
        "esperado_kw": a.esperado,
        "observado_kw": a.observado,
        "z": a.z,
        "janela_baseline": {"inicio": _ts(a.janela_inicio), "fim": _ts(a.janela_fim)},
        "top_shap": None if a.top_shap is None else [{"feature": c.feature, "shap": c.shap} for c in a.top_shap],
        "baseline_fraca": a.baseline_fraca,
        "status": STATUS_CANDIDATO,
    }


def montar_alertas(r: ResultadoM3) -> dict[str, object]:
    d = r.deteccao
    return {
        "versao_esquema": VERSAO_ESQUEMA,
        "sensor_id": r.parametros.sensor_id,
        "periodo": {"inicio": _ts(d.inicio), "fim": _ts(d.fim)},
        "limiar_z": d.limiar,
        "aviso": "Candidatos nao corroborados: nao ha rotulo real; nenhuma precisao/recall e reportada.",
        "alertas": [_alerta(a) for a in d.alertas],
    }


def montar_economia(r: ResultadoM3) -> dict[str, object]:
    ad = r.antes_depois
    red = ad.reducao
    if red is None:
        raise ValueError("economia.json exige a reducao sintetica")
    por_eq = []
    for eq, c in ad.por_equipamento.items():
        ctrl = r.controle.por_equipamento[eq]
        por_eq.append(
            {
                "equipamento": eq,
                "kwh_antes": c.kwh_antes,
                "kwh_depois": c.kwh_depois,
                "kwh_contrafactual": _num(c.kwh_contrafactual),
                "economia_kwh": _num(c.economia_kwh),
                "economia_pct": _num(c.economia_pct),
                "economia_pct_sem_reducao": _num(ctrl.economia_pct),
                "recuperado_pct_com_reducao_sintetica": _num(r.varredura_recuperado_pct[eq]),
                "reducao_sintetica_aplicada": eq == red.equipamento,
                "baseline_fraca": c.baseline_fraca,
            }
        )
    return {
        "versao_esquema": VERSAO_ESQUEMA,
        "sensor_id": r.parametros.sensor_id,
        "natureza": "validacao_de_metodo_sintetica",
        "aviso": "Reducao sintetica conhecida aplicada a dado real; valida o METODO, nao e economia real.",
        "periodo_antes": {"inicio": _ts(ad.inicio_antes), "fim": _ts(ad.fim_antes)},
        "periodo_depois": {"inicio": _ts(ad.fim_antes), "fim": _ts(ad.fim_depois)},
        "reducao_sintetica": {
            "equipamento": red.equipamento,
            "fracao_pct": 100.0 * red.fracao,
            "a_partir_de": _ts(red.a_partir_de),
        },
        "recuperado_pct": _num(ad.recuperado_pct),
        "tolerancia_pp": ad.tolerancia_pp,
        "dentro_da_tolerancia": ad.dentro_da_tolerancia,
        "equipamentos": por_eq,
    }


def _janela(j: JanelaResumo) -> dict[str, str]:
    return {"inicio": _ts(j.inicio), "fim": _ts(j.fim)}


def montar_resumo_json(r: ResumoM3) -> dict[str, object]:
    d, m, s, b = r.dados, r.mae, r.shap, r.benchmark_sintetico
    return {
        "versao_esquema": VERSAO_ESQUEMA,
        "sensor_id": r.sensor_id,
        "dados": {
            "fonte": d.fonte,
            "periodo": _janela(d.periodo),
            "treino": _janela(d.treino),
            "reservado": _janela(d.reservado),
            "equipamentos_no_andar": d.equipamentos_no_andar,
            "equipamentos_modelados": d.equipamentos_modelados,
            "equipamentos_sem_carga": list(d.equipamentos_sem_carga),
            "linhas_minuto": d.linhas_minuto,
        },
        "mae": {
            "unidade": "kW",
            "horas_teste": m.horas_teste,
            "baseline_sazonal": round(m.baseline_sazonal_kw, 4),
            "lightgbm": round(m.lightgbm_kw, 4),
            "melhora_mediana_pct": round(m.melhora_mediana_pct, 1),
            "ressalva_nowcast": m.ressalva_nowcast,
            "por_equipamento": [
                {
                    "equipamento": e.equipamento,
                    "horas_teste": e.horas_teste,
                    "mae_baseline_kw": round(e.mae_baseline_kw, 4),
                    "mae_lightgbm_kw": round(e.mae_lightgbm_kw, 4),
                    "melhora_pct": round(e.melhora_pct, 1),
                }
                for e in m.por_equipamento
            ],
        },
        "shap": {
            "horas_equipamento": s.horas_equipamento,
            "calendario_pct": round(s.calendario_pct, 1),
            "historico_pct": round(s.historico_pct, 1),
            "limiar_feature_dominante_pct": s.limiar_feature_dominante_pct,
            "por_feature": [{"feature": f.feature, "pct": round(f.pct, 1)} for f in s.por_feature],
            "por_equipamento": [
                {
                    "equipamento": e.equipamento,
                    "calendario_pct": round(e.calendario_pct, 1),
                    "historico_pct": round(e.historico_pct, 1),
                    "feature_dominante": e.feature_dominante,
                }
                for e in s.por_equipamento
            ],
        },
        "benchmark_sintetico": {
            "semente": b.semente,
            "eventos_por_tipo_por_equipamento": b.eventos_por_tipo_por_equipamento,
            "limiar_z": b.limiar_z,
            "detectores": [
                {
                    "detector": x.detector,
                    "por_tipo": [{"tipo": t.tipo, "detectados": t.detectados, "eventos": t.eventos} for t in x.por_tipo],
                    "total_detectados": x.total_detectados,
                    "total_eventos": x.total_eventos,
                    "falso_alarme_horas": x.falso_alarme_horas,
                    "horas_base": x.horas_base,
                }
                for x in b.detectores
            ],
        },
        "baseline_fraca": {
            "criterio": r.baseline_fraca.criterio,
            "semanas_completas_treino": r.baseline_fraca.semanas_completas_treino,
        },
    }


def serializar(dados: dict[str, object]) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
