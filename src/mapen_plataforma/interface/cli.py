"""CLI de provisionamento: cria empresa e chave de API. A chave sai uma vez no stdout; nada e logado.

    python -m mapen_plataforma.interface.cli criar-empresa --nome "Minha Empresa" [--principal admin] [--db caminho]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from mapen_plataforma.domain.entidades import ErroDominio
from mapen_plataforma.infrastructure.banco import BancoDuckDB
from mapen_plataforma.infrastructure.servicos import DerivadorHmac, GeradorUuid
from mapen_plataforma.interface.api.composicao import DB_M2, montar_provisionamento, segredo_mestre_do_ambiente


def criar_empresa(banco: BancoDuckDB, nome: str, principal: str = "admin") -> tuple[str, str]:
    """Devolve (empresa_id, chave_api). So o hash da chave fica no banco."""
    provisionar, _ = montar_provisionamento(banco, GeradorUuid(), DerivadorHmac(segredo_mestre_do_ambiente()))
    empresa, chave = provisionar.executar(nome, principal)
    return empresa.id, chave


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mapen_plataforma.interface.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    criar = sub.add_parser("criar-empresa", help="cria a empresa e imprime a chave de API uma unica vez")
    criar.add_argument("--nome", required=True)
    criar.add_argument("--principal", default="admin")
    criar.add_argument("--db", type=Path, default=DB_M2)
    args = parser.parse_args(argv)
    try:
        empresa_id, chave = criar_empresa(BancoDuckDB(args.db), args.nome, args.principal)
    except ErroDominio as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2
    print(f"empresa_id={empresa_id}")
    print(f"chave_api={chave}")
    print("Guarde a chave agora: ela nao e armazenada e nao pode ser recuperada.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
