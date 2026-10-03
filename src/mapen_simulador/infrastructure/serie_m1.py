"""Fonte de serie: le a tabela `leitura` do M1 pelo leitor da infraestrutura do M1 (CU-BEMS, 1 min)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from mapen_aconselhamento.infrastructure.duckdb_leituras import LeiturasDuckDB
from mapen_plataforma.domain.tempo import de_local_ingenuo, para_local_ingenuo
from mapen_simulador.domain.carga import SerieCarga
from mapen_simulador.domain.erros import ErroSimulador

PASSO_CU_BEMS = timedelta(minutes=1)


class FonteSerieM1:
    """`kwh` de cada minuto vira potencia media em W; minuto `ausente` vira `None` (lacuna, sem interpolar)."""

    def __init__(self, leituras: LeiturasDuckDB, sensor_id: str) -> None:
        self._leituras = leituras
        self._sensor_id = sensor_id

    def carregar(self, equipamento: str, inicio: datetime, duracao: timedelta) -> SerieCarga:
        ini, fim = para_local_ingenuo(inicio, "inicio"), para_local_ingenuo(inicio + duracao, "fim")
        tabela = self._leituras.ler_leituras(self._sensor_id, pd.Timestamp(ini), pd.Timestamp(fim))
        tabela = tabela[tabela["equipamento_id"] == equipamento]
        if tabela.empty:
            raise ErroSimulador(f"sem leituras de {equipamento!r} no sensor {self._sensor_id!r} nesse periodo")
        por_ts = {
            pd.Timestamp(ts).to_pydatetime(): (None if bool(aus) or pd.isna(kwh) else float(kwh) * 1000.0 * 60.0)
            for ts, kwh, aus in zip(tabela["ts"], tabela["kwh"], tabela["ausente"], strict=True)
        }
        n = int(duracao / PASSO_CU_BEMS)
        valores = tuple(por_ts.get(ini + PASSO_CU_BEMS * i) for i in range(n))
        return SerieCarga(equipamento, de_local_ingenuo(ini), PASSO_CU_BEMS, valores)
