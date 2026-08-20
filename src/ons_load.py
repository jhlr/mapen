import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "consumo" / "ons"
CKAN = "https://dados.ons.org.br/api/3/action/package_show?id={}"


def resources(dataset_id: str) -> list[dict]:
    with urllib.request.urlopen(CKAN.format(dataset_id)) as r:
        return json.load(r)["result"]["resources"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Download datasets do portal ONS Dados Abertos (CKAN + S3).")
    ap.add_argument("dataset", help="id CKAN (ex.: curva-carga, carga-mensal, balanco-energia-subsistema)")
    ap.add_argument("--ano", default=None, help="baixa só os recursos do ano (YYYY)")
    ap.add_argument("--formato", default="parquet", help="formato dos recursos (default: parquet)")
    args = ap.parse_args()

    res = [r for r in resources(args.dataset) if (r.get("format") or "").lower() == args.formato]
    if args.ano:
        res = [r for r in res if args.ano in Path(r["url"]).name]

    out = OUT / args.dataset
    out.mkdir(parents=True, exist_ok=True)

    for r in res:
        name = Path(r["url"]).name
        dest = out / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"skip {name}")
            continue
        print(f"dl   {name}")
        subprocess.run(["curl", "-sS", "-o", str(dest), r["url"]], check=True)

    print(f"{len(res)} arquivos -> {out}")


if __name__ == "__main__":
    main()
