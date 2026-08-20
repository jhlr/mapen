"""Redflags de perdas por área — protótipo.

Cruza as duas fontes canônicas já baixadas:
- EPE `MERCADO DISTRIBUICAO UF` → perda_total_GWh + consumo por UF/mês (2013→2024).
- ANEEL SAMP-Balanço → perdas por distribuidora/mês (Saldo/Perdas na Distribuição,
  valor medido; 2003→2026), e quando há Requisitos/Energia Vendida, perda relativa.

Redflag = perda relativa fora da faixa histórica (z-score sazonal por mês > 2).

Saídas:
- data/analise/perdas_uf_mes.csv      (perda relativa UF)
- data/analise/redflags_uf.csv        (redflags por UF)
- data/analise/redflags_dist.csv      (redflags por distribuidora)
- --plot: mapa por UF (média de perda relativa + contagem de redflags) no Desktop

Uso:
  .venv/bin/python src/redflags_perdas.py [--plot] [--uf PE]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
EPE_XLSX = BASE / "data" / "consumo" / "epe" / "mercado_distribuicao.xlsx"
SAMP_PARQUET = BASE / "data" / "consumo" / "samp_balanco" / "samp-balanco.parquet"
OUT_DIR = BASE / "data" / "analise"
Z_THRESH = 2.0


def perda_uf() -> pd.DataFrame:
    df = pd.read_excel(EPE_XLSX, sheet_name="MERCADO DISTRIBUICAO UF", header=0)
    df["Data"] = pd.to_datetime(df["Data"])
    consumo = df.groupby(["Data", "UF"])["Consumo_GWh"].sum().rename("consumo_GWh")
    perda = (
        df[df["Classe"] == "ND"]
        .groupby(["Data", "UF"])["perda_total_GWh"]
        .sum()
        .rename("perda_GWh")
    )
    out = pd.concat([consumo, perda], axis=1).dropna(subset=["perda_GWh"])
    out = out[out["perda_GWh"] > 0]
    out["perda_rel"] = out["perda_GWh"] / (out["consumo_GWh"] + out["perda_GWh"])
    out = out.reset_index().rename(columns={"Data": "data"})
    return out


def perda_dist() -> pd.DataFrame:
    con = duckdb.connect()
    sql = f"""
    SELECT NomAgente AS dist, AnoReferenciaBalanco AS ano, MesReferenciaBalanco AS mes,
      SUM(CASE WHEN DscFluxoEnergia='Saldo'
                    AND DscModalidadeBalanco='Perdas na Distribuição (valor medido)'
               THEN VlrEnergia ELSE 0 END) AS perdas_kwh
    FROM read_parquet('{SAMP_PARQUET}')
    GROUP BY 1, 2, 3
    """
    df = con.execute(sql).df()
    df = df[df["perdas_kwh"] > 0]
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))
    df["perda_GWh"] = df["perdas_kwh"] / 1e6
    return df[["dist", "data", "perda_GWh"]]


def redflags(df: pd.DataFrame, key: str, value: str) -> pd.DataFrame:
    """z-score sazonal (por mês do ano) do valor; flag se z > 2.

    UF usa `perda_rel`; distribuidora usa `perda_GWh` absoluto (o SAMP mede
    perda com definição diferente da EPE — normalizar por vendida/disponibilidade
    distorce, ver docs/redflags_perdas_prototipo.md).
    """
    df = df.copy()
    df["mes"] = df["data"].dt.month
    stats = df.groupby([key, "mes"])[value].agg(["mean", "std"])
    df = df.merge(stats, left_on=[key, "mes"], right_index=True)
    df["z"] = (df[value] - df["mean"]) / df["std"].replace(0, pd.NA)
    df["redflag"] = df["z"] > Z_THRESH
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plot", action="store_true", help="gera mapa por UF no Desktop")
    ap.add_argument("--uf", default=None, help="foco em uma UF (ex.: PE)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    uf = perda_uf()
    rf_uf = redflags(uf, "UF", "perda_rel")
    rf_uf.to_csv(OUT_DIR / "redflags_uf.csv", index=False)
    uf.to_csv(OUT_DIR / "perdas_uf_mes.csv", index=False)

    dist = perda_dist()
    rf_dist = redflags(dist, "dist", "perda_GWh")
    rf_dist.to_csv(OUT_DIR / "redflags_dist.csv", index=False)

    print(f"=== UF {len(uf)} ({uf.data.min():%Y-%m} → {uf.data.max():%Y-%m}), "
          f"{rf_uf.redflag.sum()} redflags ===")
    top = (
        rf_uf[rf_uf["redflag"]]
        .sort_values("z", ascending=False)
        .groupby("UF")
        .head(5)
        .sort_values("z", ascending=False)
    )
    print(top[["UF", "data", "perda_rel", "z"]].head(20).to_string(index=False))

    print(f"\n=== Distribuidoras: {dist.dist.nunique()} ({dist.data.min():%Y-%m} → "
          f"{dist.data.max():%Y-%m}), {rf_dist.redflag.sum()} redflags ===")
    topd = (
        rf_dist[rf_dist["redflag"]]
        .sort_values("z", ascending=False)
        .groupby("dist")
        .head(3)
        .sort_values("z", ascending=False)
    )
    print(topd[["dist", "data", "perda_GWh", "z"]].head(15).to_string(index=False))

    if args.uf:
        sel = rf_uf[rf_uf["UF"] == args.uf]
        print(f"\n=== FOCO {args.uf} ===")
        print(f"perda_rel média 2019+={sel[sel['data']>='2019-01-01'].perda_rel.mean():.1%} | "
              f"redflags={sel.redflag.sum()}")
        print(sel.tail(12)[["data", "consumo_GWh", "perda_GWh", "perda_rel", "z", "redflag"]]
              .to_string(index=False))

    if args.plot:
        plot_uf(uf, rf_uf)


def plot_uf(uf: pd.DataFrame, rf_uf: pd.DataFrame) -> None:
    import json

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    malha = json.loads((BASE / "data" / "br_ufs.json").read_text())["features"]
    uf_cod = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
        "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
        "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
        "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
    }
    recente = uf[uf["data"] >= "2019-01-01"].groupby("UF")["perda_rel"].mean()
    nflags = rf_uf[rf_uf["redflag"]].groupby("UF").size()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 9), dpi=160)
    for ax, values, title, cmap in (
        (ax1, recente, "Perda relativa média 2019-2024 (perdas / mercado)", "YlOrRd"),
        (ax2, nflags, "Nº de redflags (perda relativa fora da faixa histórica)", "YlOrBr"),
    ):
        vmax = values.max()
        norm = mcolors.Normalize(vmin=0, vmax=vmax)
        cm = plt.get_cmap(cmap)
        for feat in malha:
            uf_nome = uf_cod[feat["properties"]["codarea"]]
            val = values.get(uf_nome, 0)
            geom, coords = feat["geometry"], feat["geometry"]["coordinates"]
            rings = coords if geom["type"] == "Polygon" else [r for poly in coords for r in poly]
            for ring in rings:
                ax.fill([p[0] for p in ring], [p[1] for p in ring], color=cm(norm(val)),
                        ec="white", lw=0.6, zorder=1)
            ax.text(sum(p[0] for p in rings[0]) / len(rings[0]),
                    sum(p[1] for p in rings[0]) / len(rings[0]), uf_nome, fontsize=7,
                    ha="center", va="center", zorder=2)
        sm = plt.cm.ScalarMappable(cmap=cm, norm=norm)
        fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)
        ax.set_xlim(-75.5, -33.5)
        ax.set_ylim(-34.0, 6.5)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=13, pad=10)
        ax.set_axis_off()

    out = Path.home() / "Desktop" / "brasil_perdas_redflags.png"
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"\nmapa: {out}")


if __name__ == "__main__":
    main()
