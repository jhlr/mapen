"""Artefatos JSON do M3 para o dashboard: `alertas.json` e `economia.json`.

Esquemas documentados em docs/m3_notas.md. Os alertas sao candidatos nao corroborados (sem
rotulo real); a economia e validacao de metodo com reducao sintetica, nao economia real.
"""

from __future__ import annotations

import json
import math

import pandas as pd

from mapen_modelos.application.detectar_anomalias import STATUS_CANDIDATO, Alerta
from mapen_modelos.application.executar_m3 import ResultadoM3

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


def serializar(dados: dict[str, object]) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
