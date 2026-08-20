import argparse
import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D

BASE = Path(__file__).resolve().parent.parent
ONS_GRID = BASE / "data" / "power_grid_maps" / "ons_brasil"
ONS_LOAD = BASE / "data" / "consumo" / "ons"
MALHA = BASE / "data" / "br_ufs.json"

UF_COD = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

SUBSISTEMA = {
    "N": {"RO", "AC", "AM", "RR", "PA", "AP", "TO"},
    "NE": {"MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"},
    "S": {"PR", "SC", "RS"},
    "SE": {"MG", "ES", "RJ", "SP", "MS", "MT", "GO", "DF"},
}
UF_TO_SUB = {uf: sub for sub, ufs in SUBSISTEMA.items() for uf in ufs}

SUB_LABEL = {"N": "Norte", "NE": "Nordeste", "S": "Sul", "SE": "Sudeste/Centro-Oeste"}

KV_BINS = [(600, "#7f0000"), (500, "#d00000"), (345, "#ff8800"), (230, "#ffd400")]


def to_float(v: object) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_malha(path: Path) -> list[dict]:
    return [
        {"uf": UF_COD[f["properties"]["codarea"]], "geometry": f["geometry"]}
        for f in json.loads(path.read_text())["features"]
    ]


def load_grid(con: duckdb.DuckDBPyConnection) -> tuple[dict, list, list[tuple]]:
    sub = con.execute(
        f"SELECT nom_subestacao, val_latitude, val_longitude FROM read_parquet('{ONS_GRID}/SUBESTACAO.parquet')"
    ).fetchall()
    coords: dict[str, tuple[float, float]] = {}
    for nome, lat, lon in sub:
        la, lo = to_float(lat), to_float(lon)
        if la is None or lo is None:
            continue
        coords[(nome or "").strip().upper()] = (lo, la)

    lines = con.execute(
        f"SELECT nom_subestacao_de, nom_subestacao_para, val_niveltensao_kv FROM read_parquet('{ONS_GRID}/LINHA_TRANSMISSAO.parquet')"
    ).fetchall()
    return coords, lines, list(coords.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="Mapa de calor de carga por subsistema + malha de transmissão do SIN.")
    ap.add_argument("--ano", default="2025", help="ano dos dados ONS de carga (default 2025)")
    ap.add_argument("--out", default=str(Path.home() / "Desktop" / "brasil_consumo_rede.png"))
    args = ap.parse_args()

    con = duckdb.connect()

    f = ONS_LOAD / "balanco-energia-subsistema" / f"BALANCO_ENERGIA_SUBSISTEMA_{args.ano}.parquet"
    if not f.exists():
        raise SystemExit(f"arquivo não encontrado: {f}")
    rows = con.execute(
        f"SELECT trim(id_subsistema), AVG(val_carga) FROM read_parquet('{f}') "
        f"WHERE trim(id_subsistema) IN ('N','NE','S','SE') GROUP BY 1"
    ).fetchall()
    carga = {r[0]: r[1] for r in rows}
    vmax = max(carga.values())

    coords, lines, _ = load_grid(con)

    cmap = plt.get_cmap("YlOrRd")
    norm = mcolors.Normalize(vmin=0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(13, 12), dpi=160)
    for feat in load_malha(MALHA):
        sub = UF_TO_SUB[feat["uf"]]
        geom, c = feat["geometry"], feat["geometry"]["coordinates"]
        rings = c if geom["type"] == "Polygon" else [r for poly in c for r in poly]
        for ring in rings:
            ax.fill([p[0] for p in ring], [p[1] for p in ring],
                    color=cmap(norm(carga[sub])), ec="white", lw=0.5, zorder=1)

    drawn = 0
    for de, para, kv in lines:
        a = coords.get((de or "").strip().upper())
        b = coords.get((para or "").strip().upper())
        if a is None or b is None:
            continue
        color = "#2196f3"
        if kv is not None:
            for threshold, c in KV_BINS:
                if kv >= threshold:
                    color = c
                    break
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=0.7, alpha=0.85, zorder=2)
        drawn += 1

    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    ax.scatter(xs, ys, s=3, color="white", edgecolors="black", linewidths=0.15, zorder=3)

    ax.set_xlim(-75.5, -33.5)
    ax.set_ylim(-34.0, 6.5)
    ax.set_aspect("equal")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.02)
    cb.set_label(f"Carga média {args.ano} por subsistema (MW)", fontsize=11)

    legend = [
        Line2D([0], [0], color="#7f0000", lw=2, label="≥ 600 kV"),
        Line2D([0], [0], color="#d00000", lw=2, label="500 kV"),
        Line2D([0], [0], color="#ff8800", lw=2, label="345 kV"),
        Line2D([0], [0], color="#ffd400", lw=2, label="230 kV"),
        Line2D([0], [0], color="#2196f3", lw=2, label="< 230 kV"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=9, framealpha=0.95, title="Linhas de transmissão")

    ax.set_title(
        f"Carga de energia por subsistema + rede de transmissão do SIN ({args.ano}) — ONS",
        fontsize=15,
        pad=12,
    )
    labels = "  ".join(f"{k}: {SUB_LABEL[k]}" for k in ("N", "NE", "S", "SE"))
    ax.text(0.5, 0.015, labels, transform=ax.transAxes, ha="center", fontsize=10)
    ax.set_axis_off()

    out = Path(args.out)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"carga={carga} | linhas={drawn} | subestações={len(coords)} | {out}")


if __name__ == "__main__":
    main()
