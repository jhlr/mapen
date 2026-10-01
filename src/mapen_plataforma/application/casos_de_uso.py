"""Casos de uso: orquestram o dominio atraves das portas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_plataforma.application.portas import (
    Atuador,
    CalculadoraCusto,
    ChavesDispositivo,
    ConsumoEquipamento,
    CustoLinha,
    EmpresaRepo,
    EquipamentoRepo,
    EventoRepo,
    GeradorId,
    LeituraRepo,
    NonceStore,
    RankingLinha,
    RegraRepo,
    Relogio,
    SensorRepo,
    UnidadeRepo,
)
from mapen_plataforma.domain.comando import (
    Acao,
    ComandoRele,
    ConfiguracaoSeguranca,
    Decisao,
    autentico,
    avaliar_comando,
)
from mapen_plataforma.domain.entidades import (
    Equipamento,
    ErroDominio,
    Evento,
    Leitura,
    RegraDesligamento,
    Sensor,
    TipoEvento,
    Unidade,
)

MODALIDADES: tuple[str, ...] = ("convencional", "branca")


class NaoEncontrado(LookupError):
    """Recurso inexistente ou de outra empresa (indistinguiveis de proposito)."""


def _exigir_empresa(empresas: EmpresaRepo, empresa_id: str) -> None:
    if empresas.obter(empresa_id) is None:
        raise NaoEncontrado(f"empresa {empresa_id!r}")


@dataclass
class Cadastro:
    """Cadastro minimo de unidade, sensor, equipamento e leitura de listas, sempre por empresa."""

    empresas: EmpresaRepo
    unidades: UnidadeRepo
    sensores: SensorRepo
    equipamentos: EquipamentoRepo
    ids: GeradorId

    def criar_unidade(self, empresa_id: str, nome: str) -> Unidade:
        _exigir_empresa(self.empresas, empresa_id)
        unidade = Unidade(self.ids.novo(), empresa_id, nome)
        self.unidades.adicionar(unidade)
        return unidade

    def criar_sensor(self, empresa_id: str, unidade_id: str, nome: str, sensor_id: str | None = None) -> Sensor:
        if self.unidades.obter(empresa_id, unidade_id) is None:
            raise NaoEncontrado(f"unidade {unidade_id!r}")
        sid = sensor_id or self.ids.novo()
        if any(s.id == sid for s in self.sensores.listar(empresa_id)):
            raise ErroDominio(f"sensor {sid!r} ja existe")
        sensor = Sensor(sid, empresa_id, unidade_id, nome)
        self.sensores.adicionar(sensor)
        return sensor

    def criar_equipamento(self, empresa_id: str, sensor_id: str, nome: str, critico: bool) -> Equipamento:
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        equipamento = Equipamento(self.ids.novo(), empresa_id, sensor_id, nome, critico)
        self.equipamentos.adicionar(equipamento)
        return equipamento

    def listar_unidades(self, empresa_id: str) -> list[Unidade]:
        return self.unidades.listar(empresa_id)

    def listar_sensores(self, empresa_id: str) -> list[Sensor]:
        return self.sensores.listar(empresa_id)

    def listar_equipamentos(self, empresa_id: str) -> list[Equipamento]:
        return self.equipamentos.listar(empresa_id)


@dataclass
class RegistrarLeitura:
    sensores: SensorRepo
    leituras: LeituraRepo

    def executar(self, empresa_id: str, sensor_id: str, lote: list[Leitura]) -> int:
        """Grava o lote do sensor; reenvio nao duplica. Sensor de outra empresa: NaoEncontrado."""
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        if any(item.sensor_id != sensor_id for item in lote):
            raise ErroDominio("lote com leitura de outro sensor")
        return self.leituras.adicionar(lote)


@dataclass(frozen=True)
class ConsumoAgora:
    sensor_id: str
    ts_referencia: datetime
    potencia_w: float
    kwh_dia: float
    por_equipamento: list[ConsumoEquipamento]


@dataclass
class ConsumoAgoraEHoje:
    """'Agora' e a ultima leitura do sensor e 'hoje' e o dia dela (o dado de demo e historico)."""

    sensores: SensorRepo
    leituras: LeituraRepo

    def executar(self, empresa_id: str, sensor_id: str) -> ConsumoAgora:
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        ultimo = self.leituras.ultimo_ts(sensor_id)
        if ultimo is None:
            raise NaoEncontrado(f"sem leituras para {sensor_id!r}")
        dia = ultimo.replace(hour=0, minute=0, second=0, microsecond=0)
        por_equip = self.leituras.consumo_por_equipamento(sensor_id, dia, dia + timedelta(days=1))
        return ConsumoAgora(
            sensor_id,
            ultimo,
            self.leituras.potencia_em(sensor_id, ultimo),
            sum(c.kwh for c in por_equip),
            por_equip,
        )


def _validar_periodo(inicio: datetime, fim: datetime, modalidade: str) -> None:
    if fim <= inicio:
        raise ErroDominio("fim deve ser posterior ao inicio")
    if modalidade not in MODALIDADES:
        raise ErroDominio(f"modalidade desconhecida: {modalidade!r}")


@dataclass
class ListarConsumoECusto:
    sensores: SensorRepo
    custo: CalculadoraCusto

    def executar(
        self, empresa_id: str, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str
    ) -> list[CustoLinha]:
        _validar_periodo(inicio, fim, modalidade)
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        return self.custo.custo_por_faixa(sensor_id, inicio, fim, modalidade)


@dataclass
class RankingEquipamentos:
    sensores: SensorRepo
    custo: CalculadoraCusto

    def executar(
        self, empresa_id: str, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str, n: int
    ) -> list[RankingLinha]:
        _validar_periodo(inicio, fim, modalidade)
        if n < 1:
            raise ErroDominio("n deve ser >= 1")
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        return self.custo.ranking(sensor_id, inicio, fim, modalidade, n)


@dataclass
class CriarRegraDesligamento:
    equipamentos: EquipamentoRepo
    regras: RegraRepo
    relogio: Relogio
    ids: GeradorId

    def executar(
        self, empresa_id: str, equipamento_id: str, cron: str, ativo: bool, autorizado_por: str
    ) -> RegraDesligamento:
        equipamento = self.equipamentos.obter(empresa_id, equipamento_id)
        if equipamento is None:
            raise NaoEncontrado(f"equipamento {equipamento_id!r}")
        if equipamento.critico:
            raise ErroDominio("equipamento critico nao aceita regra de desligamento")
        regra = RegraDesligamento(
            self.ids.novo(), empresa_id, equipamento_id, cron, ativo, autorizado_por, self.relogio.agora()
        )
        self.regras.adicionar(regra)
        return regra


@dataclass
class AlterarRegra:
    regras: RegraRepo

    def executar(self, empresa_id: str, regra_id: str, ativo: bool) -> None:
        if not self.regras.definir_ativo(empresa_id, regra_id, ativo):
            raise NaoEncontrado(f"regra {regra_id!r}")


@dataclass
class ListarRegras:
    regras: RegraRepo

    def executar(self, empresa_id: str) -> list[RegraDesligamento]:
        return self.regras.listar(empresa_id)


@dataclass(frozen=True)
class ResultadoDesligamento:
    decisao: Decisao
    evento: Evento


@dataclass
class SolicitarDesligamento:
    """Verifica o comando pela politica de dominio e SEMPRE grava um Evento (inclusive rejeicao)."""

    equipamentos: EquipamentoRepo
    regras: RegraRepo
    eventos: EventoRepo
    nonces: NonceStore
    chaves: ChavesDispositivo
    atuador: Atuador
    relogio: Relogio
    ids: GeradorId
    config: ConfiguracaoSeguranca

    def executar(
        self,
        empresa_id: str,
        equipamento_id: str,
        comando: ComandoRele,
        autorizado_por: str | None,
        origem: str,
        regra_id: str | None = None,
    ) -> ResultadoDesligamento:
        equipamento = self.equipamentos.obter(empresa_id, equipamento_id)
        if equipamento is None:
            raise NaoEncontrado(f"equipamento {equipamento_id!r}")
        if regra_id is not None and not any(r.id == regra_id for r in self.regras.listar(empresa_id)):
            raise NaoEncontrado(f"regra {regra_id!r}")
        agora = self.relogio.agora()
        chave = self.chaves.chave(comando.device_id)
        nonce_repetido = False
        if autentico(comando, chave, agora):
            nonce_repetido = not self.nonces.registrar(comando.device_id, comando.nonce)
        decisao = avaliar_comando(
            comando, chave, agora, nonce_repetido, equipamento, autorizado_por, self.config
        )
        payload = {"acao": comando.acao.value, "device_id": comando.device_id}
        if decisao.aceito:
            self.atuador.aplicar(equipamento.sensor_id, equipamento.nome, comando.acao)
            tipo = (
                TipoEvento.DESLIGAMENTO_EXECUTADO
                if comando.acao is Acao.DESLIGAR
                else TipoEvento.RELIGAMENTO_EXECUTADO
            )
        else:
            tipo = TipoEvento.COMANDO_REJEITADO
            if decisao.motivo is not None:
                payload["motivo"] = decisao.motivo.value
        evento = Evento(
            self.ids.novo(), agora, tipo, empresa_id, equipamento.sensor_id, equipamento.id,
            origem, regra_id, autorizado_por, payload,
        )
        self.eventos.adicionar(evento)
        return ResultadoDesligamento(decisao, evento)


@dataclass
class ListarEventos:
    eventos: EventoRepo

    def executar(self, empresa_id: str, limite: int = 100) -> list[Evento]:
        return self.eventos.listar(empresa_id, limite)

