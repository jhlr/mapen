"""Esquemas JSON (pydantic) da API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from mapen_plataforma.application.casos_de_uso import (
    LOTE_LEITURAS_MAX,
    ConsumoAgora,
    PontoHorario,
    ResultadoDesligamento,
    SensorProvisionado,
)
from mapen_plataforma.application.portas import ConsumoEquipamento, CustoLinha, RankingLinha
from mapen_plataforma.domain.comando import PADRAO_ASSINATURA, Acao, ConfiguracaoSeguranca
from mapen_plataforma.domain.credenciais import CredenciaisNovas
from mapen_plataforma.domain.entidades import (
    Equipamento,
    Evento,
    Leitura,
    RegraDesligamento,
    Sensor,
    Unidade,
)

Nome = Annotated[str, StringConstraints(min_length=1, max_length=120)]
IdExterno = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Origem = Annotated[str, StringConstraints(min_length=1, max_length=64)]
Cron = Annotated[str, StringConstraints(min_length=9, max_length=100)]
Assinatura = Annotated[str, StringConstraints(pattern=PADRAO_ASSINATURA.pattern)]
Finito = Annotated[float, Field(allow_inf_nan=False)]


class Entrada(BaseModel):
    """Corpo de entrada: campo desconhecido (inclusive `autorizado_por`) e erro, nao e ignorado."""

    model_config = ConfigDict(extra="forbid")


class UnidadeIn(Entrada):
    nome: Nome


class UnidadeOut(BaseModel):
    id: str
    nome: str

    @classmethod
    def de(cls, u: Unidade) -> UnidadeOut:
        return cls(id=u.id, nome=u.nome)


class SensorIn(Entrada):
    unidade_id: IdExterno
    nome: Nome


class SensorOut(BaseModel):
    id: str
    unidade_id: str
    nome: str

    @classmethod
    def de(cls, s: Sensor) -> SensorOut:
        return cls(id=s.id, unidade_id=s.unidade_id, nome=s.nome)


class CredenciaisDispositivoOut(BaseModel):
    """Segredos do dispositivo; aparecem so nesta resposta."""

    token_dispositivo: str
    chave_comando: str

    @classmethod
    def de(cls, c: CredenciaisNovas) -> CredenciaisDispositivoOut:
        return cls(token_dispositivo=c.token, chave_comando=c.chave_comando)


class SensorCriadoOut(SensorOut):
    credenciais: CredenciaisDispositivoOut

    @classmethod
    def provisionado(cls, p: SensorProvisionado) -> SensorCriadoOut:
        return cls(
            id=p.sensor.id, unidade_id=p.sensor.unidade_id, nome=p.sensor.nome,
            credenciais=CredenciaisDispositivoOut.de(p.credenciais),
        )


class EquipamentoIn(Entrada):
    sensor_id: IdExterno
    nome: Nome
    critico: bool


class EquipamentoOut(BaseModel):
    id: str
    sensor_id: str
    nome: str
    critico: bool

    @classmethod
    def de(cls, e: Equipamento) -> EquipamentoOut:
        return cls(id=e.id, sensor_id=e.sensor_id, nome=e.nome, critico=e.critico)


class RegraIn(Entrada):
    equipamento_id: IdExterno
    cron: Cron
    ativo: bool = True


class RegraAtivoIn(Entrada):
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


class LeituraIn(Entrada):
    equipamento: Nome
    ts: AwareDatetime
    potencia_w: Finito | None = None
    tensao_v: Finito | None = None
    kwh: Finito | None = None
    ausente: bool = False

    def para_dominio(self, sensor_id: str) -> Leitura:
        return Leitura(sensor_id, self.equipamento, self.ts, self.potencia_w, self.tensao_v, self.kwh, self.ausente)


class LeiturasIn(Entrada):
    leituras: Annotated[list[LeituraIn], Field(max_length=LOTE_LEITURAS_MAX)]


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


class ComandoIn(Entrada):
    device_id: IdExterno
    acao: Acao
    nonce: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    emitido_em: AwareDatetime
    validade: AwareDatetime
    assinatura: Assinatura


class DesligamentoIn(Entrada):
    equipamento_id: IdExterno
    comando: ComandoIn
    origem: Origem = "api"
    regra_id: IdExterno | None = None


class ConfiguracaoIO(Entrada):
    desligamento_remoto_habilitado: bool

    @classmethod
    def de(cls, c: ConfiguracaoSeguranca) -> ConfiguracaoIO:
        return cls(desligamento_remoto_habilitado=c.desligamento_remoto_habilitado)


class PontoHorarioOut(BaseModel):
    hora: datetime
    kw: float
    faixa: str

    @classmethod
    def de(cls, p: PontoHorario) -> PontoHorarioOut:
        return cls(hora=p.hora, kw=p.kw, faixa=p.faixa)


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
