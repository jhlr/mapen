"""Controladores FastAPI finos: validam, chamam um caso de uso, mapeiam para JSON."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from mapen_plataforma.application.casos_de_uso import (
    AlterarRegra,
    Cadastro,
    ConsumoAgoraEHoje,
    CriarRegraDesligamento,
    ListarConsumoECusto,
    ListarEventos,
    ListarRegras,
    NaoEncontrado,
    RankingEquipamentos,
    RegistrarLeitura,
    SolicitarDesligamento,
)
from mapen_plataforma.application.portas import EmpresaRepo
from mapen_plataforma.domain.comando import ComandoRele
from mapen_plataforma.domain.entidades import ErroDominio
from mapen_plataforma.interface.api import esquemas as e


@dataclass
class Servicos:
    """Casos de uso ja montados (a composicao fica em `composicao.py`)."""

    empresas: EmpresaRepo
    cadastro: Cadastro
    registrar_leitura: RegistrarLeitura
    consumo_agora: ConsumoAgoraEHoje
    custo: ListarConsumoECusto
    ranking: RankingEquipamentos
    criar_regra: CriarRegraDesligamento
    alterar_regra: AlterarRegra
    listar_regras: ListarRegras
    desligar: SolicitarDesligamento
    eventos: ListarEventos


def criar_app(servicos: Servicos) -> FastAPI:
    app = FastAPI(title="MAPEN plataforma", version="0.1.0")

    @app.exception_handler(NaoEncontrado)
    async def _nao_encontrado(_: Request, erro: NaoEncontrado) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(erro)})

    @app.exception_handler(ErroDominio)
    async def _erro_dominio(_: Request, erro: ErroDominio) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(erro)})

    def empresa_id(x_empresa_id: Annotated[str, Header()]) -> str:
        if servicos.empresas.obter(x_empresa_id) is None:
            raise HTTPException(status_code=403, detail="empresa desconhecida")
        return x_empresa_id

    Empresa = Annotated[str, Depends(empresa_id)]

    @app.get("/unidades")
    def listar_unidades(emp: Empresa) -> list[e.UnidadeOut]:
        return [e.UnidadeOut.de(u) for u in servicos.cadastro.listar_unidades(emp)]

    @app.post("/unidades", status_code=201)
    def criar_unidade(corpo: e.UnidadeIn, emp: Empresa) -> e.UnidadeOut:
        return e.UnidadeOut.de(servicos.cadastro.criar_unidade(emp, corpo.nome))

    @app.get("/sensores")
    def listar_sensores(emp: Empresa) -> list[e.SensorOut]:
        return [e.SensorOut.de(s) for s in servicos.cadastro.listar_sensores(emp)]

    @app.post("/sensores", status_code=201)
    def criar_sensor(corpo: e.SensorIn, emp: Empresa) -> e.SensorOut:
        return e.SensorOut.de(servicos.cadastro.criar_sensor(emp, corpo.unidade_id, corpo.nome, corpo.id))

    @app.get("/equipamentos")
    def listar_equipamentos(emp: Empresa) -> list[e.EquipamentoOut]:
        return [e.EquipamentoOut.de(x) for x in servicos.cadastro.listar_equipamentos(emp)]

    @app.post("/equipamentos", status_code=201)
    def criar_equipamento(corpo: e.EquipamentoIn, emp: Empresa) -> e.EquipamentoOut:
        return e.EquipamentoOut.de(
            servicos.cadastro.criar_equipamento(emp, corpo.sensor_id, corpo.nome, corpo.critico)
        )

    @app.get("/regras")
    def listar_regras(emp: Empresa) -> list[e.RegraOut]:
        return [e.RegraOut.de(r) for r in servicos.listar_regras.executar(emp)]

    @app.post("/regras", status_code=201)
    def criar_regra(corpo: e.RegraIn, emp: Empresa) -> e.RegraOut:
        regra = servicos.criar_regra.executar(
            emp, corpo.equipamento_id, corpo.cron, corpo.ativo, corpo.autorizado_por
        )
        return e.RegraOut.de(regra)

    @app.patch("/regras/{regra_id}")
    def alterar_regra(regra_id: str, corpo: e.RegraAtivoIn, emp: Empresa) -> e.RegraAtivoIn:
        servicos.alterar_regra.executar(emp, regra_id, corpo.ativo)
        return corpo

    @app.post("/sensores/{sensor_id}/leituras")
    def registrar_leituras(sensor_id: str, corpo: e.LeiturasIn, emp: Empresa) -> e.LeiturasOut:
        lote = [x.para_dominio(sensor_id) for x in corpo.leituras]
        return e.LeiturasOut(gravadas=servicos.registrar_leitura.executar(emp, sensor_id, lote))

    @app.get("/sensores/{sensor_id}/consumo-agora")
    def consumo_agora(sensor_id: str, emp: Empresa) -> e.ConsumoAgoraOut:
        return e.ConsumoAgoraOut.de(servicos.consumo_agora.executar(emp, sensor_id))

    @app.get("/sensores/{sensor_id}/custo")
    def custo(
        sensor_id: str, inicio: datetime, fim: datetime, emp: Empresa, modalidade: str = "branca"
    ) -> list[e.CustoOut]:
        linhas = servicos.custo.executar(emp, sensor_id, inicio, fim, modalidade)
        return [e.CustoOut.de(x) for x in linhas]

    @app.get("/sensores/{sensor_id}/ranking")
    def ranking(
        sensor_id: str, inicio: datetime, fim: datetime, emp: Empresa, modalidade: str = "branca", n: int = 5
    ) -> list[e.RankingOut]:
        linhas = servicos.ranking.executar(emp, sensor_id, inicio, fim, modalidade, n)
        return [e.RankingOut.de(x) for x in linhas]

    @app.post("/desligamentos")
    def desligar(corpo: e.DesligamentoIn, emp: Empresa) -> JSONResponse:
        c = corpo.comando
        comando = ComandoRele(c.device_id, c.acao, c.nonce, c.validade, c.assinatura)
        resultado = servicos.desligar.executar(
            emp, corpo.equipamento_id, comando, corpo.autorizado_por, corpo.origem, corpo.regra_id
        )
        saida = e.DesligamentoOut.de(resultado)
        return JSONResponse(status_code=200 if saida.aceito else 403, content=saida.model_dump())

    @app.get("/eventos")
    def listar_eventos(emp: Empresa, limite: int = 100) -> list[e.EventoOut]:
        return [e.EventoOut.de(x) for x in servicos.eventos.executar(emp, limite)]

    return app
