import argparse
from pathlib import Path

from src.extract import Extract
from src.load import Load
from src.transform import Transform


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "av1-grupo-3-mapen" / "dados"
BASE_FILES = (
    ("base_diaria.csv", "base_diaria"),
    ("base_horaria.csv", "base_horaria"),
)


def run_etl(
    if_exists: str = "replace",
    data_dir: str | Path = DATA_DIR,
) -> dict[str, int]:
    source_dir = Path(data_dir)
    extrator = Extract()
    transformer = Transform()
    prepared_data = []

    for filename, table in BASE_FILES:
        source = source_dir / filename
        if not source.is_file():
            raise FileNotFoundError(
                f"Arquivo obrigatório do ETL não encontrado: '{source}'."
            )

        print(f"Etapa 1: extraindo '{source}'...")
        df_bruto = extrator.extract_from_directory(source)
        if df_bruto.empty:
            raise ValueError(f"A origem '{source}' não contém linhas para carregar.")

        print(f"Etapa 2: preservando os dados pré-tratados de '{filename}'...")
        prepared_data.append((table, transformer.transform_data(df_bruto)))

    loader = Load()
    results = {}
    for table, df in prepared_data:
        print(f"Etapa 3: carregando {len(df)} linhas no Neon, tabela '{table}'...")
        rows_loaded = loader.load_neon(df, table, if_exists=if_exists)
        print(f"Tabela '{table}': {rows_loaded} linhas gravadas.")
        results[table] = rows_loaded

    print("ETL concluído para base_diaria.csv e base_horaria.csv.")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Carrega base_diaria.csv e base_horaria.csv do MAPEN para tabelas "
            "correspondentes no Neon."
        )
    )
    parser.add_argument(
        "--if-exists",
        choices=("replace", "append", "fail"),
        default="replace",
        help="Comportamento se as tabelas já existirem (padrão: replace).",
    )
    args = parser.parse_args()
    run_etl(if_exists=args.if_exists)


if __name__ == "__main__":
    main()
