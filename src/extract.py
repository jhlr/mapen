from pathlib import Path

import pandas as pd


SUPPORTED_FORMATS = {".csv", ".parquet", ".pq", ".xlsx"}


class Extract:
    def extract_from_directory(self, directory_path: str | Path) -> pd.DataFrame:
        """Lê arquivos tabulares do MAPEN e registra a origem de cada linha."""
        source = Path(directory_path)
        if not source.exists():
            raise FileNotFoundError(f"O caminho '{source}' não foi encontrado.")

        if source.is_file():
            files = [source] if source.suffix.lower() in SUPPORTED_FORMATS else []
        elif source.is_dir():
            files = sorted(
                file
                for file in source.rglob("*")
                if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS
            )
        else:
            files = []

        if not files:
            raise FileNotFoundError(
                f"Nenhum arquivo CSV, Parquet ou Excel (.xlsx) encontrado em '{source}'."
            )

        dataframes = []
        for file in files:
            df = self._read_file(file)
            reserved = {"source_file", "source_row"} & set(df.columns)
            if reserved:
                raise ValueError(
                    f"'{file}' contém colunas reservadas pelo ETL: "
                    f"{', '.join(sorted(reserved))}."
                )
            df.insert(0, "source_row", range(1, len(df) + 1))
            source_file = (
                file.relative_to(source).as_posix() if source.is_dir() else file.name
            )
            df.insert(0, "source_file", source_file)
            dataframes.append(df)

        return pd.concat(dataframes, ignore_index=True, sort=False)

    @staticmethod
    def _read_file(file: Path) -> pd.DataFrame:
        suffix = file.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(file, encoding="utf-8-sig")
        if suffix in {".parquet", ".pq"}:
            return pd.read_parquet(file)
        if suffix == ".xlsx":
            return pd.read_excel(file)
        raise ValueError(f"Formato não suportado: '{file.suffix}'.")
