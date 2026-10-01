"""Controladores FastAPI finos: autenticam, validam, chamam um caso de uso, mapeiam para JSON."""

from dataclasses import dataclass
from typing import Annotated

from fastapi.exceptions import RequestValidationError
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime

from mapen_plataforma.application.casos_de_uso import (
    LIMITE_EVENTOS_MAX,
    RANKING_N_MAX,
    AlterarConfiguracao,
    AlterarRegra,
    AutenticarDispositivo,
    AutenticarEmpresa,
    Cadastro,
    ConsumoAgoraEHoje,
    ConsumoHorario,
    CriarRegraDesligamento,
    ListarConsumoECusto,
    ListarEventos,
    ListarRegras,
    NaoEncontrado,
    ObterConfiguracao,
    PedidoComando,
    RankingEquipamentos,
    RegistrarLeitura,
    SolicitarDesligamento,
)
from mapen_plataforma.application.portas import ResultadosM3Indisponiveis
from mapen_plataforma.application.resultados_m3 import (
    LIMITE_ALERTAS_MAX,
    LIMITE_ALERTAS_PADRAO,
    ConsultarEconomiaM3,
    ConsultarResumoM3,
    ListarAlertasM3,
)
from mapen_plataforma.domain.comando import Motivo
from mapen_plataforma.domain.credenciais import Principal
from mapen_plataforma.domain.entidades import ErroDominio
from mapen_plataforma.domain.resultados_m3 import FiltroAlertas, TipoAlerta
from mapen_plataforma.interface.api import esquemas as e

TAMANHO_MAX_CREDENCIAL = 256


@dataclass
class Servicos:
    """Casos de uso ja montados (a composicao fica em `composicao.py`)."""

    autenticar_empresa: AutenticarEmpresa
    autenticar_dispositivo: AutenticarDispositivo
    cadastro: Cadastro
    registrar_leitura: RegistrarLeitura
    consumo_agora: ConsumoAgoraEHoje
    consumo_horario: ConsumoHorario
    custo: ListarConsumoECusto
    ranking: RankingEquipamentos
    criar_regra: CriarRegraDesligamento
    alterar_regra: AlterarRegra
    listar_regras: ListarRegras
    obter_configuracao: ObterConfiguracao
    alterar_configuracao: AlterarConfiguracao
    desligar: SolicitarDesligamento
    eventos: ListarEventos
    resumo_m3: ConsultarResumoM3
    alertas_m3: ListarAlertasM3
    economia_m3: ConsultarEconomiaM3


def _nao_autenticado() -> HTTPException:
    return HTTPException(status_code=401, detail="nao autenticado", headers={"WWW-Authenticate": "Bearer"})


def _credencial(authorization: str | None) -> str:
    """Extrai o segredo de `Authorization: Bearer <segredo>`; qualquer defeito e 401 sem detalhe."""
    if authorization is None:
        raise _nao_autenticado()
    esquema, _, segredo = authorization.partition(" ")
    segredo = segredo.strip()
    if esquema.lower() != "bearer" or not segredo or len(segredo) > TAMANHO_MAX_CREDENCIAL:
        raise _nao_autenticado()
    return segredo


def criar_app(servicos: Servicos) -> FastAPI:
    app = FastAPI(title="MAPEN plataforma", version="0.2.0")

    @app.exception_handler(NaoEncontrado)
    async def _nao_encontrado(_: Request, erro: NaoEncontrado) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(erro)})

    @app.exception_handler(ErroDominio)
    async def _erro_dominio(_: Request, erro: ErroDominio) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(erro)})

    @app.exception_handler(ResultadosM3Indisponiveis)
    async def _m3_indisponivel(_: Request, erro: ResultadosM3Indisponiveis) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": f"resultados do M3 indisponiveis: {erro}"})

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        """422 sem ecoar o valor recebido (pode ser segredo, ou nao serializavel como NaN)."""
        detalhe = [{"loc": list(x["loc"]), "msg": x["msg"], "type": x["type"]} for x in erro.errors()]
        return JSONResponse(status_code=422, content={"detail": detalhe})

    def principal_empresa(authorization: Annotated[str | None, Header()] = None) -> Principal:
        principal = servicos.autenticar_empresa.executar(_credencial(authorization))
        if principal is None:
            raise _nao_autenticado()
        return principal

    def principal_dispositivo(sensor_id: str, authorization: Annotated[str | None, Header()] = None) -> Principal:
        principal = servicos.autenticar_dispositivo.executar(sensor_id, _credencial(authorization))
        if principal is None:
            raise _nao_autenticado()
        return principal

    Autenticado = Annotated[Principal, Depends(principal_empresa)]
    Dispositivo = Annotated[Principal, Depends(principal_dispositivo)]

    @app.get("/unidades")
    def listar_unidades(p: Autenticado) -> list[e.UnidadeOut]:
        return [e.UnidadeOut.de(u) for u in servicos.cadastro.listar_unidades(p.empresa_id)]

    @app.post("/unidades", status_code=201)
    def criar_unidade(corpo: e.UnidadeIn, p: Autenticado) -> e.UnidadeOut:
        return e.UnidadeOut.de(servicos.cadastro.criar_unidade(p.empresa_id, corpo.nome))

    @app.get("/sensores")
    def listar_sensores(p: Autenticado) -> list[e.SensorOut]:
        return [e.SensorOut.de(s) for s in servicos.cadastro.listar_sensores(p.empresa_id)]

    @app.post("/sensores", status_code=201)
    def criar_sensor(corpo: e.SensorIn, p: Autenticado) -> e.SensorCriadoOut:
        return e.SensorCriadoOut.provisionado(
            servicos.cadastro.criar_sensor(p.empresa_id, corpo.unidade_id, corpo.nome)
        )

    @app.post("/sensores/{sensor_id}/credenciais")
    def rotacionar_credenciais(sensor_id: str, p: Autenticado) -> e.CredenciaisDispositivoOut:
        return e.CredenciaisDispositivoOut.de(servicos.cadastro.rotacionar_sensor(p.empresa_id, sensor_id))

    @app.get("/equipamentos")
    def listar_equipamentos(p: Autenticado) -> list[e.EquipamentoOut]:
        return [e.EquipamentoOut.de(x) for x in servicos.cadastro.listar_equipamentos(p.empresa_id)]

    @app.post("/equipamentos", status_code=201)
    def criar_equipamento(corpo: e.EquipamentoIn, p: Autenticado) -> e.EquipamentoOut:
        return e.EquipamentoOut.de(
            servicos.cadastro.criar_equipamento(p.empresa_id, corpo.sensor_id, corpo.nome, corpo.critico)
        )

    @app.get("/regras")
    def listar_regras(p: Autenticado) -> list[e.RegraOut]:
        return [e.RegraOut.de(r) for r in servicos.listar_regras.executar(p.empresa_id)]

    @app.post("/regras", status_code=201)
    def criar_regra(corpo: e.RegraIn, p: Autenticado) -> e.RegraOut:
        return e.RegraOut.de(servicos.criar_regra.executar(p, corpo.equipamento_id, corpo.cron, corpo.ativo))

    @app.patch("/regras/{regra_id}")
    def alterar_regra(regra_id: str, corpo: e.RegraAtivoIn, p: Autenticado) -> e.RegraAtivoIn:
        servicos.alterar_regra.executar(p.empresa_id, regra_id, corpo.ativo)
        return corpo

    @app.get("/configuracao")
    def obter_configuracao(p: Autenticado) -> e.ConfiguracaoIO:
        return e.ConfiguracaoIO.de(servicos.obter_configuracao.executar(p.empresa_id))

    @app.put("/configuracao")
    def alterar_configuracao(corpo: e.ConfiguracaoIO, p: Autenticado) -> e.ConfiguracaoIO:
        return e.ConfiguracaoIO.de(
            servicos.alterar_configuracao.executar(p, corpo.desligamento_remoto_habilitado)
        )

    @app.post("/sensores/{sensor_id}/leituras")
    def registrar_leituras(sensor_id: str, corpo: e.LeiturasIn, p: Dispositivo) -> e.LeiturasOut:
        lote = [x.para_dominio(sensor_id) for x in corpo.leituras]
        return e.LeiturasOut(gravadas=servicos.registrar_leitura.executar(p.empresa_id, sensor_id, lote))

    @app.get("/sensores/{sensor_id}/consumo-agora")
    def consumo_agora(sensor_id: str, p: Autenticado) -> e.ConsumoAgoraOut:
        return e.ConsumoAgoraOut.de(servicos.consumo_agora.executar(p.empresa_id, sensor_id))

    @app.get("/sensores/{sensor_id}/custo")
    def custo(
        sensor_id: str, inicio: AwareDatetime, fim: AwareDatetime, p: Autenticado, modalidade: str = "branca"
    ) -> list[e.CustoOut]:
        linhas = servicos.custo.executar(p.empresa_id, sensor_id, inicio, fim, modalidade)
        return [e.CustoOut.de(x) for x in linhas]

    @app.get("/sensores/{sensor_id}/ranking")
    def ranking(
        sensor_id: str,
        inicio: AwareDatetime,
        fim: AwareDatetime,
        p: Autenticado,
        modalidade: str = "branca",
        n: Annotated[int, Query(ge=1, le=RANKING_N_MAX)] = 5,
    ) -> list[e.RankingOut]:
        linhas = servicos.ranking.executar(p.empresa_id, sensor_id, inicio, fim, modalidade, n)
        return [e.RankingOut.de(x) for x in linhas]

    @app.get("/consumo/horario")
    def consumo_horario(
        sensor_id: Annotated[str, Query(min_length=1, max_length=128)],
        inicio: AwareDatetime,
        fim: AwareDatetime,
        p: Autenticado,
        modalidade: str = "branca",
    ) -> list[e.PontoHorarioOut]:
        pontos = servicos.consumo_horario.executar(p.empresa_id, sensor_id, inicio, fim, modalidade)
        return [e.PontoHorarioOut.de(x) for x in pontos]

    @app.post("/desligamentos")
    def desligar(corpo: e.DesligamentoIn, p: Autenticado) -> JSONResponse:
        c = corpo.comando
        pedido = PedidoComando(c.device_id, c.acao, c.nonce, c.emitido_em, c.validade, c.assinatura)
        resultado = servicos.desligar.executar(p, corpo.equipamento_id, pedido, corpo.origem, corpo.regra_id)
        saida = e.DesligamentoOut.de(resultado)
        if saida.aceito:
            status = 200
        elif resultado.decisao.motivo is Motivo.EQUIPAMENTO_DESCONHECIDO:
            status = 404
        else:
            status = 403
        return JSONResponse(status_code=status, content=saida.model_dump())

    @app.get("/eventos")
    def listar_eventos(
        p: Autenticado, limite: Annotated[int, Query(ge=1, le=LIMITE_EVENTOS_MAX)] = 100
    ) -> list[e.EventoOut]:
        return [e.EventoOut.de(x) for x in servicos.eventos.executar(p.empresa_id, limite)]

    @app.get("/modelos/resumo")
    def resumo_modelos(p: Autenticado) -> e.ResumoOut:
        return e.ResumoOut.de(servicos.resumo_m3.executar(p.empresa_id))

    @app.get("/alertas")
    def listar_alertas(
        p: Autenticado,
        equipamento: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
        tipo: TipoAlerta | None = None,
        de: AwareDatetime | None = None,
        ate: AwareDatetime | None = None,
        limite: Annotated[int, Query(ge=1, le=LIMITE_ALERTAS_MAX)] = LIMITE_ALERTAS_PADRAO,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> e.AlertasOut:
        filtro = FiltroAlertas(equipamento, tipo, de, ate)
        return e.AlertasOut.de(servicos.alertas_m3.executar(p.empresa_id, filtro, limite, offset))

    @app.get("/economia")
    def economia(p: Autenticado) -> e.EconomiaOut:
        return e.EconomiaOut.de(servicos.economia_m3.executar(p.empresa_id))

    return app
