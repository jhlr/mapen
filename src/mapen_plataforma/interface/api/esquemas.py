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
from mapen_plataforma.application.resultados_m3 import (
    EconomiaConsultada,
    PaginaAlertas,
    ResumoConsultado,
)
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
from mapen_plataforma.domain.resultados_m3 import (
    ROTULO_ALERTA,
    AlertaM3,
    AvisoD7,
    ComparacaoEquipamento,
    ContribuicaoShap,
    DadosSubconjunto,
    DetectorSintetico,
    Janela,
    MaeEquipamento,
    ParticipacaoFeature,
    ReducaoSintetica,
    ShapEquipamento,
    Veredito,
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


# ---------------------------------------------------------------- resultados do M3

ROTULO_RESUMO = (
    "Resultados offline do M3 sobre dado real do CU-BEMS (um andar, 22 semanas de 2018), sem rotulo real "
    "e sem intervencao real; nao generaliza para o piloto."
)
ROTULO_BENCHMARK = "SINTETICO: anomalias injetadas em serie real; nao e precisao nem recall em dado real."


def _taxa(parte: int, todo: int) -> float | None:
    return None if todo == 0 else 100.0 * parte / todo


class MaeOut(BaseModel):
    unidade: str
    horas_teste: int
    baseline_sazonal_kw: float
    lightgbm_kw: float
    melhora_mediana_pct: float
    equipamentos_total: int
    equipamentos_lightgbm_melhor: int
    ressalva_nowcast: str
    por_equipamento: list[MaeEquipamento]


class ShapOut(BaseModel):
    horas_equipamento: int
    calendario_pct: float
    historico_pct: float
    por_feature: list[ParticipacaoFeature]
    por_equipamento: list[ShapEquipamento]
    aviso_d7: AvisoD7


class TaxaPorTipoOut(BaseModel):
    tipo: str
    detectados: int
    eventos: int
    taxa_deteccao_pct: float | None


class DetectorOut(BaseModel):
    detector: str
    por_tipo: list[TaxaPorTipoOut]
    total_detectados: int
    total_eventos: int
    taxa_deteccao_pct: float | None
    falso_alarme_horas: int
    horas_base: int
    taxa_falso_alarme_pct: float | None

    @classmethod
    def de(cls, d: DetectorSintetico) -> DetectorOut:
        return cls(
            detector=d.detector,
            por_tipo=[
                TaxaPorTipoOut(
                    tipo=t.tipo, detectados=t.detectados, eventos=t.eventos,
                    taxa_deteccao_pct=_taxa(t.detectados, t.eventos),
                )
                for t in d.por_tipo
            ],
            total_detectados=d.total_detectados,
            total_eventos=d.total_eventos,
            taxa_deteccao_pct=_taxa(d.total_detectados, d.total_eventos),
            falso_alarme_horas=d.falso_alarme_horas,
            horas_base=d.horas_base,
            taxa_falso_alarme_pct=_taxa(d.falso_alarme_horas, d.horas_base),
        )


class BenchmarkOut(BaseModel):
    sintetico: bool
    rotulo: str
    semente: int
    eventos_por_tipo_por_equipamento: int
    limiar_z: float
    detectores: list[DetectorOut]


class BaselineFracaOut(BaseModel):
    criterio: str
    semanas_completas_treino: int
    equipamentos: list[str]


class ResumoOut(BaseModel):
    disponivel: bool
    rotulo: str
    sensor_id: str | None
    dados: DadosSubconjunto | None
    mae: MaeOut | None
    shap: ShapOut | None
    benchmark_sintetico: BenchmarkOut | None
    baseline_fraca: BaselineFracaOut | None

    @classmethod
    def de(cls, c: ResumoConsultado) -> ResumoOut:
        r, aviso = c.resumo, c.aviso_d7
        if r is None or aviso is None:
            return cls(
                disponivel=False, rotulo=ROTULO_RESUMO, sensor_id=None, dados=None, mae=None, shap=None,
                benchmark_sintetico=None, baseline_fraca=None,
            )
        melhores = sum(1 for x in r.mae.por_equipamento if x.mae_lightgbm_kw < x.mae_baseline_kw)
        return cls(
            disponivel=True,
            rotulo=ROTULO_RESUMO,
            sensor_id=r.sensor_id,
            dados=r.dados,
            mae=MaeOut(
                unidade="kW", horas_teste=r.mae.horas_teste, baseline_sazonal_kw=r.mae.baseline_sazonal_kw,
                lightgbm_kw=r.mae.lightgbm_kw, melhora_mediana_pct=r.mae.melhora_mediana_pct,
                equipamentos_total=len(r.mae.por_equipamento), equipamentos_lightgbm_melhor=melhores,
                ressalva_nowcast=r.mae.ressalva_nowcast, por_equipamento=list(r.mae.por_equipamento),
            ),
            shap=ShapOut(
                horas_equipamento=r.shap.horas_equipamento, calendario_pct=r.shap.calendario_pct,
                historico_pct=r.shap.historico_pct, por_feature=list(r.shap.por_feature),
                por_equipamento=list(r.shap.por_equipamento), aviso_d7=aviso,
            ),
            benchmark_sintetico=BenchmarkOut(
                sintetico=True, rotulo=ROTULO_BENCHMARK, semente=r.benchmark_sintetico.semente,
                eventos_por_tipo_por_equipamento=r.benchmark_sintetico.eventos_por_tipo_por_equipamento,
                limiar_z=r.benchmark_sintetico.limiar_z,
                detectores=[DetectorOut.de(d) for d in r.benchmark_sintetico.detectores],
            ),
            baseline_fraca=BaselineFracaOut(
                criterio=r.baseline_fraca.criterio,
                semanas_completas_treino=r.baseline_fraca.semanas_completas_treino,
                equipamentos=list(c.equipamentos_baseline_fraca),
            ),
        )


class ExplicacaoOut(BaseModel):
    """Por que o alerta existe: z, esperado, observado, janela do baseline e, no LightGBM, as 3 features SHAP."""

    z: float
    esperado_kw: float
    observado_kw: float
    janela_baseline: Janela
    top_shap: list[ContribuicaoShap] | None


class AlertaOut(BaseModel):
    equipamento: str
    timestamp: datetime
    tipo: str
    rotulo: str
    baseline_fraca: bool
    explicacao: ExplicacaoOut

    @classmethod
    def de(cls, a: AlertaM3) -> AlertaOut:
        return cls(
            equipamento=a.equipamento, timestamp=a.timestamp, tipo=a.tipo, rotulo=ROTULO_ALERTA,
            baseline_fraca=a.baseline_fraca,
            explicacao=ExplicacaoOut(
                z=a.z, esperado_kw=a.esperado_kw, observado_kw=a.observado_kw,
                janela_baseline=a.janela_baseline,
                top_shap=None if a.top_shap is None else list(a.top_shap),
            ),
        )


class AlertasOut(BaseModel):
    disponivel: bool
    rotulo: str
    aviso: str | None
    limiar_z: float | None
    periodo: Janela | None
    total: int
    limite: int
    offset: int
    proximo_offset: int | None
    itens: list[AlertaOut]

    @classmethod
    def de(cls, p: PaginaAlertas) -> AlertasOut:
        proximo = p.offset + len(p.itens)
        base = p.base
        return cls(
            disponivel=base is not None,
            rotulo=ROTULO_ALERTA,
            aviso=None if base is None else base.aviso,
            limiar_z=None if base is None else base.limiar_z,
            periodo=None if base is None else base.periodo,
            total=p.total,
            limite=p.limite,
            offset=p.offset,
            proximo_offset=proximo if proximo < p.total else None,
            itens=[AlertaOut.de(a) for a in p.itens],
        )


class EconomiaOut(BaseModel):
    disponivel: bool
    valida_metodo_nao_economia_real: bool
    natureza: str | None
    aviso: str | None
    periodo_antes: Janela | None
    periodo_depois: Janela | None
    reducao_sintetica: ReducaoSintetica | None
    veredito: Veredito | None
    equipamentos: list[ComparacaoEquipamento]

    @classmethod
    def de(cls, c: EconomiaConsultada) -> EconomiaOut:
        e = c.economia
        return cls(
            disponivel=e is not None,
            valida_metodo_nao_economia_real=True,
            natureza=None if e is None else e.natureza,
            aviso=None if e is None else e.aviso,
            periodo_antes=None if e is None else e.periodo_antes,
            periodo_depois=None if e is None else e.periodo_depois,
            reducao_sintetica=None if e is None else e.reducao,
            veredito=c.veredito,
            equipamentos=list(c.comparacoes),
        )
