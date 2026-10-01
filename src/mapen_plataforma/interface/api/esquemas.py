"""Esquemas JSON (pydantic) da API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from mapen_plataforma.application.casos_de_uso import ConsumoAgora, ResultadoDesligamento
from mapen_plataforma.application.portas import ConsumoEquipamento, CustoLinha, RankingLinha
from mapen_plataforma.domain.comando import Acao
from mapen_plataforma.domain.entidades import (
    Equipamento,
    Evento,
    Leitura,
    RegraDesligamento,
    Sensor,
    Unidade,
)


class UnidadeIn(BaseModel):
    nome: str


class UnidadeOut(BaseModel):
    id: str
    nome: str

    @classmethod
    def de(cls, u: Unidade) -> UnidadeOut:
        return cls(id=u.id, nome=u.nome)


class SensorIn(BaseModel):
    unidade_id: str
    nome: str
    id: str | None = None


class SensorOut(BaseModel):
    id: str
    unidade_id: str
    nome: str

    @classmethod
    def de(cls, s: Sensor) -> SensorOut:
        return cls(id=s.id, unidade_id=s.unidade_id, nome=s.nome)


class EquipamentoIn(BaseModel):
    sensor_id: str
    nome: str
    critico: bool = False


class EquipamentoOut(BaseModel):
    id: str
    sensor_id: str
    nome: str
    critico: bool

    @classmethod
    def de(cls, e: Equipamento) -> EquipamentoOut:
        return cls(id=e.id, sensor_id=e.sensor_id, nome=e.nome, critico=e.critico)


class RegraIn(BaseModel):
    equipamento_id: str
    cron: str
    ativo: bool = True
    autorizado_por: str


class RegraAtivoIn(BaseModel):
    ativo: bool


class RegraOut(BaseModel):
    id: str
    equipamento_id: str
    cron: str
    ativo: bool
    autorizado_por: str
    criado_em: datetime

    @classmethod
    def de(cls, r: RegraDesligamento) -> RegraOut:
        return cls(
            id=r.id, equipamento_id=r.equipamento_id, cron=r.cron, ativo=r.ativo,
            autorizado_por=r.autorizado_por, criado_em=r.criado_em,
        )


class LeituraIn(BaseModel):
    equipamento: str
    ts: datetime
    potencia_w: float | None = None
    tensao_v: float | None = None
    kwh: float | None = None
    ausente: bool = False

    def para_dominio(self, sensor_id: str) -> Leitura:
        return Leitura(sensor_id, self.equipamento, self.ts, self.potencia_w, self.tensao_v, self.kwh, self.ausente)


class LeiturasIn(BaseModel):
    leituras: list[LeituraIn]


class LeiturasOut(BaseModel):
    gravadas: int


class ConsumoEquipamentoOut(BaseModel):
    equipamento: str
    kwh: float

    @classmethod
    def de(cls, c: ConsumoEquipamento) -> ConsumoEquipamentoOut:
        return cls(equipamento=c.equipamento_nome, kwh=c.kwh)


class ConsumoAgoraOut(BaseModel):
    sensor_id: str
    ts_referencia: datetime
    potencia_w: float
    kwh_dia: float
    por_equipamento: list[ConsumoEquipamentoOut]

    @classmethod
    def de(cls, c: ConsumoAgora) -> ConsumoAgoraOut:
        return cls(
            sensor_id=c.sensor_id, ts_referencia=c.ts_referencia, potencia_w=c.potencia_w,
            kwh_dia=c.kwh_dia, por_equipamento=[ConsumoEquipamentoOut.de(x) for x in c.por_equipamento],
        )


class CustoOut(BaseModel):
    equipamento: str
    faixa: str
    kwh: float
    custo_rs: float

    @classmethod
    def de(cls, c: CustoLinha) -> CustoOut:
        return cls(equipamento=c.equipamento_nome, faixa=c.faixa, kwh=c.kwh, custo_rs=c.custo_rs)


class RankingOut(BaseModel):
    equipamento: str
    kwh: float
    custo_rs: float
    pct_ausente: float

    @classmethod
    def de(cls, r: RankingLinha) -> RankingOut:
        return cls(equipamento=r.equipamento_nome, kwh=r.kwh, custo_rs=r.custo_rs, pct_ausente=r.pct_ausente)


class ComandoIn(BaseModel):
    device_id: str
    acao: Acao
    nonce: str
    validade: datetime
    assinatura: str


class DesligamentoIn(BaseModel):
    equipamento_id: str
    comando: ComandoIn
    autorizado_por: str | None = None
    origem: str = "api"
    regra_id: str | None = None


class DesligamentoOut(BaseModel):
    aceito: bool
    motivo: str | None
    evento_id: str

    @classmethod
    def de(cls, r: ResultadoDesligamento) -> DesligamentoOut:
        return cls(
            aceito=r.decisao.aceito,
            motivo=None if r.decisao.motivo is None else r.decisao.motivo.value,
            evento_id=r.evento.id,
        )


class EventoOut(BaseModel):
    id: str
    ts: datetime
    tipo: str
    sensor_id: str | None
    equipamento_id: str | None
    origem: str
    regra_id: str | None
    autorizado_por: str | None
    payload: dict[str, str]

    @classmethod
    def de(cls, e: Evento) -> EventoOut:
        return cls(
            id=e.id, ts=e.ts, tipo=e.tipo.value, sensor_id=e.sensor_id, equipamento_id=e.equipamento_id,
            origem=e.origem, regra_id=e.regra_id, autorizado_por=e.autorizado_por, payload=e.payload,
        )
