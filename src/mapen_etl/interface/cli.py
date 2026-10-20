"""CLI `mapen-etl`: carrega base_diaria.csv e base_horaria.csv da AV1 no Neon.

Variavel de ambiente: DATABASE_URL (URL PostgreSQL do Neon), tambem aceita em `.env`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from mapen_etl.application.carregar_bases import carregar_bases
from mapen_etl.domain.bases import ModoCarga
from mapen_etl.infrastructure.leitor_csv import LeitorCsv
from mapen_etl.infrastructure.neon import GravadorNeon

DIRETORIO_PADRAO = Path("av1-grupo-3-mapen/dados")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mapen-etl", description=__doc__)
    ap.add_argument(
        "--if-exists",
        choices=("fail", "append", "replace"),
        default="fail",
        help="Se a tabela ja existir: fail (padrao), append (pode duplicar) ou replace (apaga e recria).",
    )
    ap.add_argument("--data-dir", type=Path, default=DIRETORIO_PADRAO, help=f"Pasta dos CSVs (padrao {DIRETORIO_PADRAO}).")
    args = ap.parse_args(argv)
    modo: ModoCarga = args.if_exists
    resultado = carregar_bases(LeitorCsv(), GravadorNeon(), args.data_dir, modo)
    for tabela, linhas in resultado.items():
        print(f"{tabela}: {linhas} linhas gravadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
