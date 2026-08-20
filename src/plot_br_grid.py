import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BASE = Path(__file__).resolve().parent.parent
ONS = BASE / "data" / "power_grid_maps" / "ons_brasil"
IBGE = Path("/var/folders/q7/bkpgntz547n9gc64szcfxpm40000gn/T/opencode/br.geojson")


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


def load_br_outline(path: Path) -> list[list[tuple[float, float]]]:
    data = json.loads(path.read_text())
    polys: list[list[tuple[float, float]]] = []
    for feat in data.get("features", data):
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom.get("type") == "Polygon":
            polys.append(coords[0])
        elif geom.get("type") == "MultiPolygon":
            for poly in coords:
                polys.append(poly[0])
    return polys


def main() -> None:
    con = duckdb.connect()

    sub = con.execute(
        f"SELECT nom_subestacao, val_latitude, val_longitude FROM read_parquet('{ONS}/SUBESTACAO.parquet')"
    ).fetchall()
    coords: dict[str, tuple[float, float]] = {}
    for nome, lat, lon in sub:
        la, lo = to_float(lat), to_float(lon)
        if la is None or lo is None:
            continue
        coords[(nome or "").strip().upper()] = (lo, la)

    lines = con.execute(
        f"SELECT nom_subestacao_de, nom_subestacao_para, val_niveltensao_kv FROM read_parquet('{ONS}/LINHA_TRANSMISSAO.parquet')"
    ).fetchall()

    fig, ax = plt.subplots(figsize=(13, 12), dpi=160)

    outline = load_br_outline(IBGE)
    for ring in outline:
        xs, ys = zip(*ring)
        ax.plot(xs, ys, color="0.6", lw=0.8, zorder=1)

    kv_bins = [(600, "#7f0000"), (500, "#d00000"), (345, "#ff8800"), (230, "#ffd400")]
    drawn = 0
    for de, para, kv in lines:
        a = coords.get((de or "").strip().upper())
        b = coords.get((para or "").strip().upper())
        if a is None or b is None:
            continue
        color = "#2196f3"
        if kv is not None:
            for threshold, c in kv_bins:
                if kv >= threshold:
                    color = c
                    break
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=0.7, alpha=0.8, zorder=2)
        drawn += 1

    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    ax.scatter(xs, ys, s=3, color="white", edgecolors="black", linewidths=0.15, zorder=3)

    all_lons = [p[0] for ring in outline for p in ring]
    all_lats = [p[1] for ring in outline for p in ring]
    ax.set_xlim(min(all_lons) - 1, max(all_lons) + 1)
    ax.set_ylim(min(all_lats) - 1, max(all_lats) + 1)

    ax.set_title(
        "Rede de transmissão do SIN — subestações e linhas (ONS, dados abertos)",
        fontsize=15,
        pad=12,
    )
    legend = [
        Line2D([0], [0], color="#7f0000", lw=2, label="≥ 600 kV"),
        Line2D([0], [0], color="#d00000", lw=2, label="500 kV"),
        Line2D([0], [0], color="#ff8800", lw=2, label="345 kV"),
        Line2D([0], [0], color="#ffd400", lw=2, label="230 kV"),
        Line2D([0], [0], color="#2196f3", lw=2, label="< 230 kV"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=10, framealpha=0.95)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    ax.tick_params(labelsize=9)

    out = Path.home() / "Desktop" / "brasil_rede_transmissao.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"linhas plotadas: {drawn} | subestações: {len(coords)} | {out}")


if __name__ == "__main__":
    main()
