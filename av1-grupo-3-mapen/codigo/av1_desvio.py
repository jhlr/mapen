"""AV1 / Grupo 3 MAPEN: consumo observado versus referência esperada (CU-BEMS 2018 Floor 2).

Uso (da pasta av1-grupo-3-mapen):
    python codigo/av1_desvio.py                       # usa dados/recorte_minuto.csv.gz
    python codigo/av1_desvio.py --fonte <2018Floor2.csv>   # refaz o recorte a partir do arquivo original

Entrada: leituras de potência média por minuto (kW) por equipamento.
Saídas: dados/base_diaria.csv, dados/base_horaria.csv, dashboard/dados.js e
        evidencias/{verificacoes_qualidade,resultados_python}.json.

Regras (todas declaradas também no relatório):
  - energia diária (kWh) = potência média dos minutos presentes (kW) x 24 h; dia válido com >= 95% dos minutos;
  - referência = mediana da energia diária do MESMO dia da semana numa janela anterior ao intervalo avaliado;
  - desvio = observado - esperado (kWh); desvio relativo = 100 x desvio / esperado, só se esperado > 0.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Final, TypedDict

import numpy as np
import pandas as pd

RAIZ: Final = Path(__file__).resolve().parent.parent

ATIVOS: Final[list[str]] = [
    "z1_AC1", "z1_Light", "z1_Plug", "z2_Light", "z2_Plug", "z3_Light", "z4_AC1", "z4_Plug",
]
INICIO_REF: Final = pd.Timestamp("2018-09-09")  # domingo; 12 semanas antes do fim do recorte
INICIO_AVAL: Final = pd.Timestamp("2018-11-04")  # domingo
FIM_AVAL_EXCL: Final = pd.Timestamp("2018-12-02")  # exclusivo; avalia 04/11 a 01/12 (28 dias)
# Feriados tailandeses dentro da janela de referência (zero de consumo nos ativos de ar-condicionado).
FERIADOS: Final[list[str]] = ["2018-10-13", "2018-10-15", "2018-10-23"]
# Horário operacional: HIPÓTESE inferida do perfil de z1_AC1 (liga ~7h, desliga ~17-18h), não informada por ninguém.
EXPEDIENTE_INICIO: Final = 7
EXPEDIENTE_FIM: Final = 18  # exclusivo: 07h00 até 17h59
COBERTURA_MINIMA: Final = 0.95
MINUTOS_DIA: Final = 1440
MINUTOS_HORA_MINIMO: Final = 45


class JanelaRef(TypedDict):
    id: str
    nome: str
    inicio: str
    fim_excl: str
    excluir_feriados: bool


# A é a referência principal; B e C mudam uma hipótese cada (janela, calendário).
REFERENCIAS: Final[list[JanelaRef]] = [
    {"id": "A", "nome": "Mediana de 8 semanas, mesmo dia da semana", "inicio": "2018-09-09",
     "fim_excl": "2018-11-04", "excluir_feriados": False},
    {"id": "B", "nome": "Mediana de 4 semanas, mesmo dia da semana", "inicio": "2018-10-07",
     "fim_excl": "2018-11-04", "excluir_feriados": False},
    {"id": "C", "nome": "Mediana de 8 semanas sem feriados", "inicio": "2018-09-09",
     "fim_excl": "2018-11-04", "excluir_feriados": True},
]


def carregar_recorte(fonte: Path) -> pd.DataFrame:
    """Lê o CSV (original ou recorte) e devolve kW por minuto, uma coluna por ativo, na janela do estudo."""
    bruto = pd.read_csv(fonte, parse_dates=["Date"])
    colunas = {f"{a}(kW)" if f"{a}(kW)" in bruto.columns else a: a for a in ATIVOS}
    minuto = bruto.rename(columns=colunas).set_index("Date")[ATIVOS]
    return minuto.loc[INICIO_REF : FIM_AVAL_EXCL - pd.Timedelta(minutes=1)]


def gerar_recorte(fonte: Path, destino: Path) -> None:
    """Extrai do arquivo original só os ativos e o período do estudo (reprodutível sem os 5 meses)."""
    minuto = carregar_recorte(fonte)
    minuto.reset_index().to_csv(destino, index=False, float_format="%.2f", compression="gzip", lineterminator="\n")


def verificacoes_qualidade(fonte: Path) -> dict[str, object]:
    """Cinco verificações sobre o arquivo de entrada, antes de qualquer transformação."""
    bruto = pd.read_csv(fonte, parse_dates=["Date"])
    colunas_ativos = [c if c in bruto.columns else f"{c}(kW)" for c in ATIVOS]
    janela = bruto[(bruto["Date"] >= INICIO_REF) & (bruto["Date"] < FIM_AVAL_EXCL)]
    grade = pd.date_range(INICIO_REF, FIM_AVAL_EXCL - pd.Timedelta(minutes=1), freq="min")
    valores = janela[colunas_ativos]
    por_dia = janela.set_index("Date")[colunas_ativos].notna().resample("D").sum()
    dias_baixa_cobertura = (por_dia < COBERTURA_MINIMA * MINUTOS_DIA).sum()
    return {
        "1_chaves_duplicidade": {
            "linhas_na_janela": int(len(janela)),
            "timestamps_duplicados": int(janela["Date"].duplicated().sum()),
        },
        "2_ausencia": {
            "timestamps_ausentes_na_grade_de_1_min": int(len(grade.difference(pd.DatetimeIndex(janela["Date"])))),
            "minutos_sem_valor_por_ativo": {a: int(valores[c].isna().sum()) for a, c in zip(ATIVOS, colunas_ativos)},
        },
        "3_tipos_unidades": {
            "tipos": {a: str(valores[c].dtype) for a, c in zip(ATIVOS, colunas_ativos)},
            "unidade_original": "kW (potência média por minuto), conforme o sufixo '(kW)' do cabeçalho",
        },
        "4_dominio_plausibilidade": {
            "negativos": {a: int((valores[c] < 0).sum()) for a, c in zip(ATIVOS, colunas_ativos)},
            "maximo_kw": {a: float(valores[c].max()) for a, c in zip(ATIVOS, colunas_ativos)},
            "ativos_com_maximo_zero": [a for a, c in zip(ATIVOS, colunas_ativos) if valores[c].max() == 0],
        },
        "5_cobertura": {
            "dias_na_janela": int(len(por_dia)),
            "dias_com_menos_de_95pct_dos_minutos": {a: int(dias_baixa_cobertura[c]) for a, c in zip(ATIVOS, colunas_ativos)},
            "juncoes": "nenhuma: a base é uma única tabela; sem junção, a cardinalidade não muda",
        },
    }


def tipo_dia(d: pd.Timestamp) -> str:
    return "fim_de_semana" if d.dayofweek >= 5 else "dia_util"


def base_diaria(minuto: pd.DataFrame) -> pd.DataFrame:
    """Energia diária em kWh = potência média dos minutos presentes x 24 h, com cobertura e validade."""
    media_kw = minuto.resample("D").mean()
    presentes = minuto.notna().resample("D").sum()
    longa = pd.DataFrame(
        {
            "kwh": (media_kw * 24).stack(),
            "minutos_validos": presentes.stack(),
        }
    ).reset_index()
    longa.columns = pd.Index(["data", "ativo", "kwh", "minutos_validos"])
    longa["valido"] = longa["minutos_validos"] >= COBERTURA_MINIMA * MINUTOS_DIA
    longa.loc[~longa["valido"], "kwh"] = np.nan
    longa["tipo_dia"] = longa["data"].map(tipo_dia)
    longa["feriado"] = longa["data"].dt.strftime("%Y-%m-%d").isin(FERIADOS)
    return longa.sort_values(["ativo", "data"]).reset_index(drop=True)


def base_horaria(minuto: pd.DataFrame) -> pd.DataFrame:
    """Potência média por hora (kW); hora com menos de 45 minutos vira ausência."""
    media = minuto.resample("h").mean()
    presentes = minuto.notna().resample("h").sum()
    media = media.where(presentes >= MINUTOS_HORA_MINIMO)
    longa = media.stack(future_stack=True).rename("kw").reset_index()
    longa.columns = pd.Index(["inicio_hora", "ativo", "kw"])
    dia = longa["inicio_hora"].dt.normalize()
    util = longa["inicio_hora"].dt.dayofweek < 5
    feriado = dia.dt.strftime("%Y-%m-%d").isin(FERIADOS)
    hora = longa["inicio_hora"].dt.hour
    longa["expediente"] = util & ~feriado & (hora >= EXPEDIENTE_INICIO) & (hora < EXPEDIENTE_FIM)
    return longa.sort_values(["ativo", "inicio_hora"]).reset_index(drop=True)


def esperado_diario(diaria: pd.DataFrame, ref: JanelaRef) -> pd.DataFrame:
    """Esperado por (ativo, data avaliada): mediana dos dias válidos da janela com o mesmo dia da semana."""
    inicio, fim = pd.Timestamp(ref["inicio"]), pd.Timestamp(ref["fim_excl"])
    janela = diaria[(diaria["data"] >= inicio) & (diaria["data"] < fim) & diaria["valido"]]
    if ref["excluir_feriados"]:
        janela = janela[~janela["feriado"]]
    mediana = (
        janela.assign(dsem=janela["data"].dt.dayofweek)
        .groupby(["ativo", "dsem"])["kwh"]
        .median()
    )
    aval = diaria[(diaria["data"] >= INICIO_AVAL) & (diaria["data"] < FIM_AVAL_EXCL)].copy()
    aval["dsem"] = aval["data"].dt.dayofweek
    aval["esperado"] = [mediana.get((a, s), np.nan) for a, s in zip(aval["ativo"], aval["dsem"])]
    aval["desvio"] = aval["kwh"] - aval["esperado"]
    aval["desvio_rel_pct"] = np.where(aval["esperado"] > 0, 100 * aval["desvio"] / aval["esperado"], np.nan)
    aval["ref"] = ref["id"]
    return aval.drop(columns=["dsem"])


def ranking(desvios: pd.DataFrame) -> pd.DataFrame:
    """Soma dos desvios positivos (ordem, empate pelo nome), soma dos negativos e saldo, por ativo, em kWh."""
    d = desvios.dropna(subset=["desvio"])
    agg = d.groupby("ativo").agg(
        soma_positivos=("desvio", lambda s: float(s[s > 0].sum())),
        soma_negativos=("desvio", lambda s: float(s[s < 0].sum())),
        saldo=("desvio", "sum"),
        dias_validos=("desvio", "size"),
        observado=("kwh", "sum"),
        esperado=("esperado", "sum"),
    )
    # Empate: nome do ativo, como no painel (dashboard/calculo.js). Sem isso a ordem dos empatados muda com a versão do pandas.
    return agg.reset_index().sort_values(["soma_positivos", "ativo"], ascending=[False, True]).reset_index(drop=True)


def perfil_horario(horaria: pd.DataFrame, diaria: pd.DataFrame, ref: JanelaRef) -> pd.DataFrame:
    """Mediana, entre dias, da potência média por hora do dia, por tipo de dia: observado x referência."""
    h = horaria.copy()
    h["data"] = h["inicio_hora"].dt.normalize()
    h["hora"] = h["inicio_hora"].dt.hour
    h["tipo_dia"] = h["data"].map(tipo_dia)
    h = h.merge(diaria[["ativo", "data", "valido", "feriado"]], on=["ativo", "data"])
    h = h[h["valido"]]
    inicio, fim = pd.Timestamp(ref["inicio"]), pd.Timestamp(ref["fim_excl"])
    obs = h[(h["data"] >= INICIO_AVAL) & (h["data"] < FIM_AVAL_EXCL)]
    base = h[(h["data"] >= inicio) & (h["data"] < fim)]
    if ref["excluir_feriados"]:
        base = base[~base["feriado"]]
    chaves = ["ativo", "tipo_dia", "hora"]
    o = obs.groupby(chaves)["kw"].median().rename("observado_kw")
    r = base.groupby(chaves)["kw"].median().rename("referencia_kw")
    return pd.concat([o, r], axis=1).reset_index().assign(ref=ref["id"])


def dados_js(diaria: pd.DataFrame, horaria: pd.DataFrame) -> str:
    """Base compacta para o painel recalcular no navegador (mesma janela de 84 dias)."""
    datas = sorted(diaria["data"].dt.strftime("%Y-%m-%d").unique())
    pivot = diaria.pivot(index="data", columns="ativo", values="kwh")
    horas = horaria.assign(data=horaria["inicio_hora"].dt.strftime("%Y-%m-%d"), hora=horaria["inicio_hora"].dt.hour)
    pacote = {
        "fonte": "CU-BEMS, andar 2 (Floor2), 2018. Dado real público, não é cliente nem medição do MAPEN.",
        "datas": datas,
        "inicio_avaliacao": INICIO_AVAL.strftime("%Y-%m-%d"),
        "fim_avaliacao_exclusivo": FIM_AVAL_EXCL.strftime("%Y-%m-%d"),
        "feriados": FERIADOS,
        "expediente": {"inicio": EXPEDIENTE_INICIO, "fim": EXPEDIENTE_FIM, "natureza": "hipótese inferida do perfil, não informada"},
        "referencias": REFERENCIAS,
        "ativos": ATIVOS,
        "diario": {a: [None if np.isnan(v) else round(float(v), 4) for v in pivot[a].to_numpy()] for a in ATIVOS},
        "horario": {
            a: [
                [None if np.isnan(v) else round(float(v), 3) for v in horas[(horas["ativo"] == a) & (horas["data"] == d)]
                 .sort_values("hora")["kw"].to_numpy()]
                for d in datas
            ]
            for a in ATIVOS
        },
    }
    return "window.MAPEN_DADOS = " + json.dumps(pacote, ensure_ascii=False, separators=(",", ":")) + ";\n"


def sensibilidade(rankings: dict[str, pd.DataFrame], desvios: dict[str, pd.DataFrame]) -> dict[str, object]:
    """Mudou o ativo/dia priorizado quando a referência muda?"""
    topo = {r: rk.iloc[0]["ativo"] for r, rk in rankings.items()}
    ordem = {r: list(rk["ativo"]) for r, rk in rankings.items()}
    pior_dia: dict[str, dict[str, object]] = {}
    for r, d in desvios.items():
        x = d.dropna(subset=["desvio"])
        linha = x.loc[x["desvio"].idxmax()]
        pior_dia[r] = {"ativo": linha["ativo"], "data": linha["data"].strftime("%Y-%m-%d"), "desvio_kwh": round(float(linha["desvio"]), 2)}
    return {"ativo_no_topo_por_referencia": topo, "ordem_por_referencia": ordem, "maior_desvio_diario_por_referencia": pior_dia}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, help="2018Floor2.csv original (opcional)")
    args = ap.parse_args()
    recorte = RAIZ / "dados" / "recorte_minuto.csv.gz"
    if args.fonte:
        gerar_recorte(args.fonte, recorte)
        qualidade = verificacoes_qualidade(args.fonte)
        (RAIZ / "evidencias" / "verificacoes_qualidade.json").write_text(
            json.dumps(qualidade, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
    minuto = carregar_recorte(recorte)
    diaria, horaria = base_diaria(minuto), base_horaria(minuto)
    diaria.to_csv(RAIZ / "dados" / "base_diaria.csv", index=False, float_format="%.4f", lineterminator="\n")
    horaria.to_csv(RAIZ / "dados" / "base_horaria.csv", index=False, float_format="%.3f", lineterminator="\n")
    (RAIZ / "dashboard" / "dados.js").write_text(dados_js(diaria, horaria), encoding="utf-8", newline="\n")

    desvios = {r["id"]: esperado_diario(diaria, r) for r in REFERENCIAS}
    rankings = {k: ranking(v) for k, v in desvios.items()}
    saida = {
        "ranking": {k: v.round(3).to_dict(orient="records") for k, v in rankings.items()},
        "sensibilidade": sensibilidade(rankings, desvios),
        "desvios_diarios": {
            k: v.assign(data=v["data"].dt.strftime("%Y-%m-%d"))[
                ["ativo", "data", "kwh", "esperado", "desvio", "desvio_rel_pct"]
            ].round(4).replace({np.nan: None}).to_dict(orient="records")
            for k, v in desvios.items()
        },
    }
    (RAIZ / "evidencias" / "resultados_python.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    print(json.dumps(saida["sensibilidade"], ensure_ascii=False, indent=1))
    for k, v in rankings.items():
        print(f"\nReferência {k}\n{v.round(1).to_string(index=False)}")


if __name__ == "__main__":
    main()
