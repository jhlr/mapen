"""Casos de uso: orquestram o dominio atraves das portas."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from mapen_plataforma.application.portas import (
    Atuador,
    CalculadoraCusto,
    CredenciaisDispositivoRepo,
    CredenciaisEmpresaRepo,
    CredencialDispositivo,
    ChavesDispositivo,
    ConfiguracaoRepo,
    ConsumoEquipamento,
    CustoLinha,
    DerivadorChave,
    EmpresaRepo,
    EquipamentoRepo,
    ErroAtuador,
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
    Motivo,
    avaliar_comando,
    expira_o_nonce_em,
)
from mapen_plataforma.domain.credenciais import (
    CredenciaisNovas,
    Principal,
    gerar_segredo,
    hash_segredo,
    segredo_confere,
)
from mapen_plataforma.domain.entidades import (
    Empresa,
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
LIMITE_EVENTOS_MAX = 500
RANKING_N_MAX = 100
LOTE_LEITURAS_MAX = 5000
PERIODO_HORARIO_MAX = timedelta(days=31)
TAMANHO_MIN_CHAVE = 32


class NaoEncontrado(LookupError):
    """Recurso inexistente ou de outra empresa (indistinguiveis de proposito)."""


def _exigir_nome(valor: str, campo: str) -> None:
    if not valor.strip():
        raise ErroDominio(f"{campo} nao pode ser vazio")


# --- autenticacao e provisionamento -------------------------------------------------------


@dataclass
class AutenticarEmpresa:
    credenciais: CredenciaisEmpresaRepo

    def executar(self, chave: str) -> Principal | None:
        """Principal dono da chave, ou None. A chave nunca e guardada, so o hash."""
        principal = self.credenciais.buscar(hash_segredo(chave))
        return principal


@dataclass
class AutenticarDispositivo:
    credenciais: CredenciaisDispositivoRepo

    def executar(self, device_id: str, token: str) -> Principal | None:
        credencial = self.credenciais.obter(device_id)
        if credencial is None or not segredo_confere(token, credencial.token_hash):
            return None
        return Principal(credencial.empresa_id, device_id)


@dataclass
class ProvisionarEmpresa:
    """Cria a empresa (se nova) e a chave de API do principal. A chave sai uma vez, no retorno."""

    empresas: EmpresaRepo
    credenciais: CredenciaisEmpresaRepo
    ids: GeradorId

    def executar(
        self, nome: str, principal: str = "admin", empresa_id: str | None = None, chave: str | None = None
    ) -> tuple[Empresa, str]:
        _exigir_nome(nome, "nome")
        _exigir_nome(principal, "principal")
        existente = None if empresa_id is None else self.empresas.obter(empresa_id)
        empresa = existente or Empresa(empresa_id or self.ids.novo(), nome)
        if existente is None:
            self.empresas.adicionar(empresa)
        segredo = chave if chave is not None else gerar_segredo()
        if len(segredo) < TAMANHO_MIN_CHAVE:
            raise ErroDominio(f"chave deve ter ao menos {TAMANHO_MIN_CHAVE} caracteres")
        self.credenciais.definir(empresa.id, principal, hash_segredo(segredo))
        return empresa, segredo


@dataclass
class EmitirCredenciaisDispositivo:
    """Token de ingestao e chave de comando novos para o dispositivo; os antigos deixam de valer.

    Serve para o primeiro provisionamento e para a rotacao. So hash e sal sao guardados.
    """

    credenciais: CredenciaisDispositivoRepo
    derivador: DerivadorChave

    def executar(self, empresa_id: str, device_id: str) -> CredenciaisNovas:
        token, sal = gerar_segredo(), gerar_segredo()
        self.credenciais.definir(CredencialDispositivo(device_id, empresa_id, hash_segredo(token), sal))
        return CredenciaisNovas(token, self.derivador.derivar(device_id, sal).hex())


# --- cadastro ----------------------------------------------------------------------------


@dataclass(frozen=True)
class SensorProvisionado:
    sensor: Sensor
    credenciais: CredenciaisNovas


@dataclass
class Cadastro:
    """Cadastro de unidade, sensor, equipamento e listagens, sempre por empresa."""

    empresas: EmpresaRepo
    unidades: UnidadeRepo
    sensores: SensorRepo
    equipamentos: EquipamentoRepo
    emitir: EmitirCredenciaisDispositivo
    ids: GeradorId

    def criar_unidade(self, empresa_id: str, nome: str) -> Unidade:
        _exigir_nome(nome, "nome")
        if self.empresas.obter(empresa_id) is None:
            raise NaoEncontrado("empresa")
        unidade = Unidade(self.ids.novo(), empresa_id, nome)
        self.unidades.adicionar(unidade)
        return unidade

    def criar_sensor(self, empresa_id: str, unidade_id: str, nome: str) -> SensorProvisionado:
        """O id e sempre gerado aqui (uuid4): o cliente nao escolhe identidade de dispositivo."""
        _exigir_nome(nome, "nome")
        if self.unidades.obter(empresa_id, unidade_id) is None:
            raise NaoEncontrado(f"unidade {unidade_id!r}")
        sensor = Sensor(self.ids.novo(), empresa_id, unidade_id, nome)
        self.sensores.adicionar(sensor)
        return SensorProvisionado(sensor, self.emitir.executar(empresa_id, sensor.id))

    def rotacionar_sensor(self, empresa_id: str, sensor_id: str) -> CredenciaisNovas:
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        return self.emitir.executar(empresa_id, sensor_id)

    def criar_equipamento(self, empresa_id: str, sensor_id: str, nome: str, critico: bool) -> Equipamento:
        _exigir_nome(nome, "nome")
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


# --- leituras e consumo ------------------------------------------------------------------


@dataclass
class RegistrarLeitura:
    sensores: SensorRepo
    leituras: LeituraRepo

    def executar(self, empresa_id: str, sensor_id: str, lote: list[Leitura]) -> int:
        """Grava o lote do sensor; reenvio nao duplica. Sensor de outra empresa: NaoEncontrado."""
        if len(lote) > LOTE_LEITURAS_MAX:
            raise ErroDominio(f"lote acima de {LOTE_LEITURAS_MAX} leituras")
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        return self.leituras.adicionar([replace(item, sensor_id=sensor_id) for item in lote])


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
    if inicio.tzinfo is None or fim.tzinfo is None:
        raise ErroDominio("inicio e fim devem ter fuso horario")
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
        if not 1 <= n <= RANKING_N_MAX:
            raise ErroDominio(f"n deve estar entre 1 e {RANKING_N_MAX}")
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        return self.custo.ranking(sensor_id, inicio, fim, modalidade, n)


@dataclass(frozen=True)
class PontoHorario:
    hora: datetime
    kw: float
    faixa: str


@dataclass
class ConsumoHorario:
    """Serie horaria de kW com a faixa tarifaria de cada hora.

    O banco soma o kWh por hora; aqui o kWh vira kW (media da hora) e a faixa vem do M1
    (`CalculadoraCusto.faixas`), sem repetir a regra de horarios.
    """

    sensores: SensorRepo
    leituras: LeituraRepo
    custo: CalculadoraCusto

    def executar(
        self, empresa_id: str, sensor_id: str, inicio: datetime, fim: datetime, modalidade: str
    ) -> list[PontoHorario]:
        _validar_periodo(inicio, fim, modalidade)
        if fim - inicio > PERIODO_HORARIO_MAX:
            raise ErroDominio(f"periodo acima de {PERIODO_HORARIO_MAX.days} dias")
        if self.sensores.obter(empresa_id, sensor_id) is None:
            raise NaoEncontrado(f"sensor {sensor_id!r}")
        horas = self.leituras.consumo_horario(sensor_id, inicio, fim)
        faixas = self.custo.faixas([h.hora for h in horas], modalidade)
        return [PontoHorario(h.hora, h.kwh, f) for h, f in zip(horas, faixas, strict=True)]


# --- regras e configuracao ---------------------------------------------------------------


@dataclass
class CriarRegraDesligamento:
    equipamentos: EquipamentoRepo
    regras: RegraRepo
    relogio: Relogio
    ids: GeradorId

    def executar(
        self, principal: Principal, equipamento_id: str, cron: str, ativo: bool
    ) -> RegraDesligamento:
        """`autorizado_por` e o nome do principal autenticado, nunca um dado do corpo."""
        equipamento = self.equipamentos.obter(principal.empresa_id, equipamento_id)
        if equipamento is None:
            raise NaoEncontrado(f"equipamento {equipamento_id!r}")
        if equipamento.critico:
            raise ErroDominio("equipamento critico nao aceita regra de desligamento")
        regra = RegraDesligamento(
            self.ids.novo(), principal.empresa_id, equipamento_id, cron, ativo, principal.nome,
            self.relogio.agora(),
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


@dataclass
class ObterConfiguracao:
    configuracao: ConfiguracaoRepo

    def executar(self, empresa_id: str) -> ConfiguracaoSeguranca:
        return self.configuracao.obter(empresa_id)


@dataclass
class AlterarConfiguracao:
    """Liga/desliga o desligamento remoto da empresa; o evento (com o principal) vem antes da mudanca."""

    configuracao: ConfiguracaoRepo
    eventos: EventoRepo
    relogio: Relogio
    ids: GeradorId

    def executar(self, principal: Principal, habilitado: bool) -> ConfiguracaoSeguranca:
        antes = self.configuracao.obter(principal.empresa_id)
        self.eventos.adicionar(
            Evento(
                self.ids.novo(), self.relogio.agora(), TipoEvento.CONFIGURACAO_ALTERADA,
                principal.empresa_id, None, None, "api", None, principal.nome,
                {
                    "desligamento_remoto_habilitado_antes": str(antes.desligamento_remoto_habilitado).lower(),
                    "desligamento_remoto_habilitado": str(habilitado).lower(),
                },
            )
        )
        nova = ConfiguracaoSeguranca(habilitado)
        self.configuracao.definir(principal.empresa_id, nova)
        return nova


# --- desligamento ------------------------------------------------------------------------


@dataclass(frozen=True)
class PedidoComando:
    """Campos do comando como o cliente os envia; empresa e equipamento vem da requisicao autenticada."""

    device_id: str
    acao: Acao
    nonce: str
    emitido_em: datetime
    validade: datetime
    assinatura: str


@dataclass(frozen=True)
class ResultadoDesligamento:
    decisao: Decisao
    evento: Evento


@dataclass
class SolicitarDesligamento:
    """Aplica a politica de dominio e deixa rastro de TODO pedido.

    Ordem: evento de intencao, (se aceito) atuador, evento de resultado. Se gravar a intencao
    falhar, a excecao sobe e o atuador nao e chamado.
    """

    equipamentos: EquipamentoRepo
    regras: RegraRepo
    eventos: EventoRepo
    nonces: NonceStore
    chaves: ChavesDispositivo
    configuracao: ConfiguracaoRepo
    atuador: Atuador
    relogio: Relogio
    ids: GeradorId

    def executar(
        self,
        principal: Principal,
        equipamento_id: str,
        pedido: PedidoComando,
        origem: str,
        regra_id: str | None = None,
    ) -> ResultadoDesligamento:
        empresa_id = principal.empresa_id
        agora = self.relogio.agora()
        equipamento = self.equipamentos.obter(empresa_id, equipamento_id)
        payload = {
            "acao": pedido.acao.value,
            "device_id": pedido.device_id,
            "equipamento_solicitado": equipamento_id,
            "nonce": pedido.nonce,
        }
        intencao = Evento(
            self.ids.novo(), agora, TipoEvento.COMANDO_RECEBIDO, empresa_id,
            None if equipamento is None else equipamento.sensor_id,
            None if equipamento is None else equipamento.id,
            origem, regra_id, principal.nome, dict(payload),
        )
        self.eventos.adicionar(intencao)
        payload["intencao_id"] = intencao.id
        if equipamento is None:
            return self._concluir(intencao, Decisao(False, Motivo.EQUIPAMENTO_DESCONHECIDO), payload)
        try:
            comando = ComandoRele(
                pedido.device_id, empresa_id, equipamento.id, pedido.acao, pedido.nonce,
                pedido.emitido_em, pedido.validade, pedido.assinatura,
            )
        except ErroDominio:
            return self._concluir(intencao, Decisao(False, Motivo.COMANDO_MALFORMADO), payload)
        self.nonces.podar(agora)
        regra = None if regra_id is None else self.regras.obter(empresa_id, regra_id)
        regra_valida = regra_id is None or (
            regra is not None and regra.ativo and regra.equipamento_id == equipamento.id
        )
        decisao = avaliar_comando(
            comando,
            self.chaves.chave(pedido.device_id),
            agora,
            lambda: self.nonces.registrar(pedido.device_id, pedido.nonce, expira_o_nonce_em(comando)),
            equipamento,
            regra_valida,
            principal.nome,
            self.configuracao.obter(empresa_id),
        )
        if decisao.aceito:
            try:
                self.atuador.aplicar(equipamento.sensor_id, equipamento.nome, comando.acao)
            except ErroAtuador:
                return self._concluir(
                    intencao, Decisao(False, Motivo.FALHA_ATUADOR), payload, TipoEvento.FALHA_CONEXAO
                )
        return self._concluir(intencao, decisao, payload)

    def _concluir(
        self, intencao: Evento, decisao: Decisao, payload: dict[str, str], tipo_falha: TipoEvento | None = None
    ) -> ResultadoDesligamento:
        if decisao.aceito:
            tipo = (
                TipoEvento.DESLIGAMENTO_EXECUTADO
                if payload["acao"] == Acao.DESLIGAR.value
                else TipoEvento.RELIGAMENTO_EXECUTADO
            )
        else:
            tipo = tipo_falha or TipoEvento.COMANDO_REJEITADO
            if decisao.motivo is not None:
                payload = {**payload, "motivo": decisao.motivo.value}
        resultado = replace(intencao, id=self.ids.novo(), tipo=tipo, payload=payload)
        self.eventos.adicionar(resultado)
        return ResultadoDesligamento(decisao, resultado)


@dataclass
class ListarEventos:
    eventos: EventoRepo

    def executar(self, empresa_id: str, limite: int = 100) -> list[Evento]:
        if not 1 <= limite <= LIMITE_EVENTOS_MAX:
            raise ErroDominio(f"limite deve estar entre 1 e {LIMITE_EVENTOS_MAX}")
        return self.eventos.listar(empresa_id, limite)
