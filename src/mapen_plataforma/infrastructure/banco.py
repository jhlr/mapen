"""Conexao DuckDB compartilhada (com trava) e esquema das tabelas."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from pathlib import Path

import duckdb

from mapen_aconselhamento.infrastructure.duckdb_leituras import DDL_LEITURA

DDL: tuple[str, ...] = (
    DDL_LEITURA,
    "CREATE TABLE IF NOT EXISTS empresa (id VARCHAR PRIMARY KEY, nome VARCHAR)",
    "CREATE TABLE IF NOT EXISTS unidade (id VARCHAR PRIMARY KEY, empresa_id VARCHAR, nome VARCHAR)",
    "CREATE TABLE IF NOT EXISTS sensor "
    "(id VARCHAR PRIMARY KEY, empresa_id VARCHAR, unidade_id VARCHAR, nome VARCHAR)",
    "CREATE TABLE IF NOT EXISTS equipamento "
    "(id VARCHAR PRIMARY KEY, empresa_id VARCHAR, sensor_id VARCHAR, nome VARCHAR, critico BOOLEAN)",
    "CREATE TABLE IF NOT EXISTS regra_desligamento (id VARCHAR PRIMARY KEY, empresa_id VARCHAR, "
    "equipamento_id VARCHAR, cron VARCHAR, ativo BOOLEAN, autorizado_por VARCHAR, criado_em TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS evento (id VARCHAR PRIMARY KEY, ts TIMESTAMP, tipo VARCHAR, "
    "empresa_id VARCHAR, sensor_id VARCHAR, equipamento_id VARCHAR, origem VARCHAR, "
    "regra_id VARCHAR, autorizado_por VARCHAR, payload VARCHAR)",
    "CREATE TABLE IF NOT EXISTS nonce (device_id VARCHAR, nonce VARCHAR, expira_em TIMESTAMP, "
    "PRIMARY KEY (device_id, nonce))",
    "ALTER TABLE nonce ADD COLUMN IF NOT EXISTS expira_em TIMESTAMP",
    "CREATE TABLE IF NOT EXISTS credencial_empresa (hash_chave VARCHAR PRIMARY KEY, empresa_id VARCHAR, "
    "principal VARCHAR, criado_em TIMESTAMP DEFAULT current_timestamp, UNIQUE (empresa_id, principal))",
    "CREATE TABLE IF NOT EXISTS credencial_dispositivo (device_id VARCHAR PRIMARY KEY, empresa_id VARCHAR, "
    "token_hash VARCHAR, sal VARCHAR, atualizado_em TIMESTAMP DEFAULT current_timestamp)",
    "CREATE TABLE IF NOT EXISTS configuracao_empresa "
    "(empresa_id VARCHAR PRIMARY KEY, desligamento_remoto_habilitado BOOLEAN)",
)


class BancoDuckDB:
    """Uma conexao, serializada por trava (o duckdb nao e seguro para uso concorrente)."""

    def __init__(self, caminho: str | Path = ":memory:") -> None:
        self.conexao = duckdb.connect(str(caminho))
        self.trava = threading.RLock()
        for ddl in DDL:
            self.conexao.execute(ddl)

    def executar(self, sql: str, params: Sequence[object] = ()) -> None:
        with self.trava:
            self.conexao.execute(sql, list(params))

    def consultar(self, sql: str, params: Sequence[object] = ()) -> list[tuple[object, ...]]:
        with self.trava:
            return self.conexao.execute(sql, list(params)).fetchall()
