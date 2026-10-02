"""CLI `mapen-simulador`: simula o firmware do dispositivo e emite comandos assinados contra a API.

Variaveis de ambiente (nenhum segredo vai em argumento de linha de comando):

    MAPEN_SIM_URL            URL da API (padrao http://127.0.0.1:8000)
    MAPEN_SIM_TOKEN          token do dispositivo, para `simular`
    MAPEN_SIM_CHAVE_API      chave Bearer da empresa, para `emitir`
    MAPEN_SIM_CHAVE_COMANDO  chave de comando do dispositivo em hexadecimal, para `emitir`
    MAPEN_SEGREDO_MESTRE     alternativa a MAPEN_SIM_CHAVE_COMANDO, junto com MAPEN_SIM_SAL:
    MAPEN_SIM_SAL            sal do dispositivo (a chave e derivada como a plataforma faz)
    MAPEN_DB_M1              banco do M1 com a CU-BEMS (padrao data/mapen_m1.duckdb)
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from mapen_aconselhamento.infrastructure.caminhos import RAIZ
from mapen_aconselhamento.infrastructure.duckdb_leituras import LeiturasDuckDB, conectar
from mapen_plataforma.domain.comando import Acao
from mapen_plataforma.domain.tempo import FUSO_LOCAL
from mapen_simulador.application.casos_de_uso import EmitirComando, PedidoSimulacao, SimularSensor
from mapen_simulador.application.portas import ProvedorChaves
from mapen_simulador.domain.dispositivo import ConfigDispositivo
from mapen_simulador.domain.erros import ErroSimulador
from mapen_simulador.domain.relatorio import RelatorioSimulacao
from mapen_simulador.infrastructure.api_http import EnvioComandoHttp, EnvioEventosHttp, EnvioLeiturasHttp
from mapen_simulador.infrastructure.cenario_json import CenarioRelativo, ler_cenario
from mapen_simulador.infrastructure.chaves import ChaveDerivada, ChaveFixa
from mapen_simulador.infrastructure.nonces import NonceUuid
from mapen_simulador.infrastructure.relogio import RelogioSistema
from mapen_simulador.infrastructure.serie_m1 import FonteSerieM1

URL_PADRAO = "http://127.0.0.1:8000"
DB_M1_PADRAO = RAIZ / "data" / "mapen_m1.duckdb"
SENSOR_FONTE_PADRAO = "cu_bems_2018Floor2"


def _exigir_env(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise ErroSimulador(f"defina a variavel de ambiente {nome}")
    return valor


def _janela(texto: str) -> tuple[float, float]:
    """`INICIO_MIN:DURACAO_MIN`, em minutos desde o inicio da simulacao."""
    ini, _, dur = texto.partition(":")
    try:
        return float(ini), float(dur)
    except ValueError as erro:
        raise argparse.ArgumentTypeError(f"esperado INICIO_MIN:DURACAO_MIN, recebi {texto!r}") from erro


def _data(texto: str) -> datetime:
    """ISO 8601; sem fuso, vale a hora local de America/Recife."""
    valor = datetime.fromisoformat(texto)
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=FUSO_LOCAL)


def _json(relatorio: RelatorioSimulacao) -> str:
    def padrao(o: object) -> str:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, enum.Enum):
            return str(o.value)
        raise TypeError(type(o).__name__)

    return json.dumps(dataclasses.asdict(relatorio), default=padrao, indent=2)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mapen-simulador", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("simular", help="repete uma serie do M1 como dispositivo, com quedas de Wi-Fi e de energia")
    s.add_argument("--sensor-id", required=True, help="id do sensor/dispositivo na API")
    s.add_argument("--equipamento", required=True, help="coluna da CU-BEMS, ex.: z1_AC1")
    s.add_argument("--fonte-sensor", default=SENSOR_FONTE_PADRAO, help="sensor do M1 de onde ler a serie")
    s.add_argument("--db", type=Path, default=Path(os.environ.get("MAPEN_DB_M1", str(DB_M1_PADRAO))))
    s.add_argument("--inicio", type=_data, required=True, help="inicio da serie no M1 (ISO; sem fuso = Recife)")
    s.add_argument("--minutos", type=int, default=120)
    s.add_argument("--reiniciar-em", type=_data, default=None, help="novo eixo de tempo (ex.: o presente)")
    s.add_argument("--cenario", type=Path, default=None, help="arquivo JSON de cenario (ver cenario_json.py)")
    s.add_argument("--wifi-fora", type=_janela, action="append", default=[], metavar="INI:DUR")
    s.add_argument("--energia-fora", type=_janela, action="append", default=[], metavar="INI:DUR")
    s.add_argument("--bateria-min", type=float, default=None)
    s.add_argument("--deriva-ppm", type=float, default=None)
    s.add_argument("--lote", type=int, default=500)
    e = sub.add_parser("emitir", help="assina e envia um comando ligar/desligar")
    e.add_argument("--device-id", required=True)
    e.add_argument("--empresa-id", required=True)
    e.add_argument("--equipamento-id", required=True)
    e.add_argument("--acao", choices=[a.value for a in Acao], required=True)
    e.add_argument("--validade-s", type=float, default=30.0, help="ate 60")
    e.add_argument("--origem", default="simulador")
    e.add_argument("--regra-id", default=None)
    for sp in (s, e):
        sp.add_argument("--url", default=os.environ.get("MAPEN_SIM_URL", URL_PADRAO))
    return p


def _cenario_relativo(args: argparse.Namespace) -> CenarioRelativo:
    base = ler_cenario(args.cenario) if args.cenario else CenarioRelativo()
    return CenarioRelativo(
        wifi=base.wifi + tuple(args.wifi_fora),
        energia=base.energia + tuple(args.energia_fora),
        bateria_min=base.bateria_min if args.bateria_min is None else args.bateria_min,
        deriva_ppm=base.deriva_ppm if args.deriva_ppm is None else args.deriva_ppm,
    )


def _simular(args: argparse.Namespace) -> int:
    rel = _cenario_relativo(args)
    inicio = args.reiniciar_em or args.inicio
    pedido = PedidoSimulacao(
        ConfigDispositivo(args.sensor_id, tamanho_lote=args.lote, deriva_ppm=rel.deriva_ppm),
        args.equipamento, args.inicio, timedelta(minutes=args.minutos), rel.a_partir_de(inicio), args.reiniciar_em,
    )
    con = conectar(args.db)
    with httpx.Client(base_url=args.url, timeout=30.0) as client:
        token = _exigir_env("MAPEN_SIM_TOKEN")
        caso = SimularSensor(
            FonteSerieM1(LeiturasDuckDB(con), args.fonte_sensor),
            EnvioLeiturasHttp(client, args.sensor_id, token),
            EnvioEventosHttp(client, args.sensor_id, token),
        )
        print(_json(caso.executar(pedido)))
    return 0


def _chaves(device_id: str) -> ProvedorChaves:
    hexa = os.environ.get("MAPEN_SIM_CHAVE_COMANDO")
    if hexa:
        return ChaveFixa({device_id: hexa})
    return ChaveDerivada(_exigir_env("MAPEN_SEGREDO_MESTRE").encode(), {device_id: _exigir_env("MAPEN_SIM_SAL")})


def _emitir(args: argparse.Namespace) -> int:
    with httpx.Client(base_url=args.url, timeout=30.0) as client:
        caso = EmitirComando(
            _chaves(args.device_id), RelogioSistema(), NonceUuid(),
            EnvioComandoHttp(client, _exigir_env("MAPEN_SIM_CHAVE_API")),
        )
        r = caso.executar(
            args.device_id, args.empresa_id, args.equipamento_id, Acao(args.acao), args.validade_s,
            origem=args.origem, regra_id=args.regra_id,
        )
    print(json.dumps({"aceito": r.resposta.aceito, "status": r.resposta.status, "motivo": r.resposta.motivo}))
    return 0 if r.resposta.aceito else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _simular(args) if args.comando == "simular" else _emitir(args)
    except (ErroSimulador, httpx.HTTPError) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
