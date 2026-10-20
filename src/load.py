import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


class Load:
    def __init__(self, database_url: str | None = None) -> None:
        load_dotenv()
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "Configure DATABASE_URL no ambiente ou no arquivo .env para conectar ao Neon."
            )
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace(
                "postgres://", "postgresql+psycopg://", 1
            )
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )

    def load_neon(
        self,
        df: pd.DataFrame,
        nome_tabela: str,
        if_exists: str = "replace",
    ) -> int:
        """Grava o DataFrame em uma tabela PostgreSQL do Neon e retorna linhas gravadas."""
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nome_tabela):
            raise ValueError(
                "O nome da tabela deve começar por letra ou _ e conter apenas "
                "letras ASCII, números e _."
            )
        if if_exists not in {"fail", "replace", "append"}:
            raise ValueError("if_exists deve ser 'fail', 'replace' ou 'append'.")
        if df.empty:
            raise ValueError("Não há dados para carregar no Neon.")

        engine = create_engine(self.database_url)
        try:
            return int(
                df.to_sql(
                    nome_tabela,
                    engine,
                    if_exists=if_exists,
                    index=False,
                )
            )
        finally:
            engine.dispose()
