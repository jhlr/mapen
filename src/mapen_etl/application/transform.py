"""Etapa Transform. As bases chegam pre-tratadas (decisao do projeto): o conteudo segue sem alteracao."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class Transform:
    def transform_data(self, conteudo: T) -> T:
        return conteudo
