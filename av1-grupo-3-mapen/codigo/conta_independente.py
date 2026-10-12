"""Conta independente: refaz à mão (stdlib, sem pandas) o esperado e o desvio de um ativo/dia e compara com a base.

Uso: python codigo/conta_independente.py [ativo] [data ISO] [referencia A|B|C]
Lê dados/recorte_minuto.csv.gz (entrada) e dados/base_diaria.csv + resultados_python.json (exibido).
"""

from __future__ import annotations

import csv
import gzip
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JANELAS = {"A": ("2018-09-09", "2018-11-04", False), "B": ("2018-10-07", "2018-11-04", False), "C": ("2018-09-09", "2018-11-04", True)}
FERIADOS = {"2018-10-13", "2018-10-15", "2018-10-23"}


def energia_diaria(ativo: str) -> dict[str, float]:
    soma: dict[str, float] = {}
    n: dict[str, int] = {}
    with gzip.open(RAIZ / "dados" / "recorte_minuto.csv.gz", "rt", newline="") as f:
        for linha in csv.DictReader(f):
            v = linha[ativo]
            if v == "":
                continue
            d = linha["Date"][:10]
            soma[d] = soma.get(d, 0.0) + float(v)
            n[d] = n.get(d, 0) + 1
    # kWh/dia = média dos minutos presentes (kW) x 24 h; dia válido com >= 95% de 1440 minutos
    return {d: soma[d] / n[d] * 24 for d in soma if n[d] >= 0.95 * 1440}


def main() -> None:
    ativo = sys.argv[1] if len(sys.argv) > 1 else "z1_AC1"
    alvo = sys.argv[2] if len(sys.argv) > 2 else "2018-11-12"
    ref = sys.argv[3] if len(sys.argv) > 3 else "A"
    ini, fim, sem_feriados = JANELAS[ref]
    kwh = energia_diaria(ativo)
    dsem = date.fromisoformat(alvo).weekday()
    d, amostra = date.fromisoformat(ini), []
    while d < date.fromisoformat(fim):
        iso = d.isoformat()
        if d.weekday() == dsem and iso in kwh and not (sem_feriados and iso in FERIADOS):
            amostra.append((iso, kwh[iso]))
        d += timedelta(days=1)
    esperado = statistics.median(v for _, v in amostra)
    observado = kwh[alvo]
    desvio = observado - esperado
    exibido = next(x for x in json.loads((RAIZ / "evidencias" / "resultados_python.json").read_text())["desvios_diarios"][ref]
                   if x["ativo"] == ativo and x["data"] == alvo)
    print(f"ativo={ativo} data={alvo} referencia={ref}")
    print("dias da referência (mesmo dia da semana):", [(i, round(v, 2)) for i, v in amostra])
    print(f"observado={observado:.4f} esperado={esperado:.4f} desvio={desvio:.4f} kWh")
    print(f"exibido (pipeline): observado={exibido['kwh']} esperado={exibido['esperado']} desvio={exibido['desvio']}")
    dif = max(abs(observado - exibido["kwh"]), abs(esperado - exibido["esperado"]), abs(desvio - exibido["desvio"]))
    print(f"maior diferença absoluta = {dif:.5f} kWh -> {'OK' if dif < 5e-4 else 'DIVERGE'}")
    sys.exit(0 if dif < 5e-4 else 1)


if __name__ == "__main__":
    main()
