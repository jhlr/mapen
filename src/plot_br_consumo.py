import argparse
import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

BASE = Path(__file__).resolve().parent.parent
ONS = BASE / "data" / "consumo" / "ons"
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


def load_malha(path: Path) -> list[dict]:
    feats = json.loads(path.read_text())["features"]
    out = []
    for f in feats:
        out.append({"uf": UF_COD[f["properties"]["codarea"]], "geometry": f["geometry"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Mapa de calor de carga/consumo por subsistema no mapa do Brasil.")
    ap.add_argument("--ano", default="2025", help="ano dos dados ONS (default 2025)")
    ap.add_argument("--fonte", default="balanco", choices=["balanco", "curva-carga"])
    ap.add_argument("--out", default=str(Path.home() / "Desktop" / "brasil_consumo.png"))
    args = ap.parse_args()

    col = "val_carga" if args.fonte == "balanco" else "val_cargaenergiahomwmed"
    folder = "balanco-energia-subsistema" if args.fonte == "balanco" else "curva-carga"
    f = ONS / folder / (f"BALANCO_ENERGIA_SUBSISTEMA_{args.ano}.parquet" if args.fonte == "balanco"
                        else f"CURVA_CARGA_{args.ano}.parquet")
    if not f.exists():
        raise SystemExit(f"arquivo não encontrado: {f}")

    con = duckdb.connect()
    rows = con.execute(
        f"SELECT trim(id_subsistema), AVG({col}) FROM read_parquet('{f}') "
        f"WHERE trim(id_subsistema) IN ('N','NE','S','SE') GROUP BY 1"
    ).fetchall()
    carga = {r[0]: r[1] for r in rows}
    vmax = max(carga.values())

    cmap = plt.get_cmap("YlOrRd")
    norm = mcolors.Normalize(vmin=0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(12, 11), dpi=160)
    for feat in load_malha(MALHA):
        sub = UF_TO_SUB[feat["uf"]]
        geom, coords = feat["geometry"], feat["geometry"]["coordinates"]
        rings = coords if geom["type"] == "Polygon" else [r for poly in coords for r in poly]
        for ring in rings:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            ax.fill(xs, ys, color=cmap(norm(carga[sub])), ec="white", lw=0.6, zorder=1)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label(f"Carga média {args.ano} (MW)", fontsize=12)

    ax.set_xlim(-75.5, -33.5)
    ax.set_ylim(-34.0, 6.5)
    ax.set_aspect("equal")
    ax.set_title(
        f"Carga de energia por subsistema do SIN ({args.ano}) — ONS dados abertos",
        fontsize=15,
        pad=12,
    )
    ax.set_axis_off()

    labels = "  ".join(f"{k}: {SUB_LABEL[k]}" for k in ("N", "NE", "S", "SE"))
    ax.text(0.5, 0.02, labels, transform=ax.transAxes, ha="center", fontsize=11)

    out = Path(args.out)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"carga por subsistema: {carga} | {out}")


if __name__ == "__main__":
    main()
