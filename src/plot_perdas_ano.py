"""Gráfico de linha temporal — perda de energia no Brasil por ano.

Agrega `data/analise/perdas_uf_mes.csv` (todas as UFs) por ano. Um único eixo:
linha de perda relativa média (%) com marcadores por ano, pico e vale anotados;
a perda total (GWh) fica como rótulo direto em cada ponto (sem dual-axis).

Uso:
  .venv/bin/python src/plot_perdas_ano.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "data" / "analise" / "perdas_uf_mes.csv"
OUT = Path.home() / "Desktop" / "mapen_perdas_por_ano.png"

LINE = "#2e6f95"
PEAK = "#c0392b"
VALE = "#1e8f5f"
INK = "#1c1c1c"
MUTED = "#6b6b6b"


def main() -> None:
    df = duckdb.sql(f"""
        select
            strftime(data::date, '%Y') as ano,
            sum(perda_GWh) as perda_total_gwh,
            avg(perda_rel) * 100 as perda_rel_media_pct
        from read_csv_auto('{CSV}')
        group by ano
        order by ano
    """).df()

    x = range(len(df))
    y = df["perda_rel_media_pct"]
    imax, imin = y.idxmax(), y.idxmin()

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(12, 6.5))

    ax.plot(x, y, color=LINE, linewidth=2, zorder=3)
    ax.fill_between(x, y, y.min() * 0.9, color=LINE, alpha=0.08, zorder=1)
    ax.scatter(x, y, s=28, color=LINE, zorder=4, edgecolor="white", linewidth=0.8)

    for i in (imax, imin):
        color = PEAK if i == imax else VALE
        ax.scatter([i], [y[i]], s=90, color=color, zorder=5, edgecolor="white", linewidth=1.2)
        label = f"{df['ano'][i]} · pico {y[i]:.1f}%" if i == imax else f"{df['ano'][i]} · vale {y[i]:.1f}%"
        va = "bottom" if i == imax else "top"
        offset = 0.6 if i == imax else -0.6
        ax.annotate(label, (i, y[i] + offset), ha="center", va=va,
                    fontsize=9, color=color, fontweight="bold")

    for i, gwh in zip(x, df["perda_total_gwh"]):
        if i == imax:
            offset = (0, -34)
        elif i == imin:
            offset = (0, 16)
        else:
            offset = (0, -16)
        ax.annotate(f"{gwh / 1000:.0f}k GWh", (i, y[i]), textcoords="offset points",
                    xytext=offset, ha="center", va="top" if offset[1] < 0 else "bottom",
                    fontsize=6.5, color=MUTED, alpha=0.85, rotation=90)

    fig.suptitle("Perda de energia no Brasil por ano", x=0.02, y=0.99,
                 ha="left", fontsize=15, color=INK, fontweight="bold")
    fig.text(0.02, 0.925, "Perda relativa média (%); rótulo = perda total em GWh — EPE, UFs agregadas",
              ha="left", fontsize=9.5, color=MUTED)

    ax.set_ylabel("Perda relativa média (%)", fontsize=10, color=MUTED)
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["ano"], rotation=45, ha="right")
    ax.set_ylim(y.min() * 0.9, y.max() * 1.15)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(axis="x", labelsize=9, colors=INK)
    ax.tick_params(axis="y", labelsize=9, colors=MUTED)
    ax.yaxis.grid(True, color="#e6e6e6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"salvo em {OUT}")


if __name__ == "__main__":
    main()
