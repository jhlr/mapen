"""Casos de uso do simulador: SimularSensor (repete uma serie com cenario de falhas) e EmitirComando."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_plataforma.domain.comando import Acao, ComandoRele
from mapen_simulador.application.portas import (
    EnvioComando,
    EnvioEventos,
    EnvioLeituras,
    FonteSerie,
    GeradorNonce,
    ProvedorChaves,
    RespostaComando,
    Relogio,
)
from mapen_simulador.domain.cenario import Cenario
from mapen_simulador.domain.comando import construir_comando
from mapen_simulador.domain.dispositivo import ConfigDispositivo, DispositivoSimulado
from mapen_simulador.domain.erros import ErroSimulador
from mapen_simulador.domain.relatorio import RelatorioSimulacao


@dataclass(frozen=True)
class PedidoSimulacao:
    """`reiniciar_em` coloca a serie historica num novo eixo de tempo (ex.: o presente)."""

    config: ConfigDispositivo
    equipamento: str
    inicio_fonte: datetime
    duracao: timedelta
    cenario: Cenario
    reiniciar_em: datetime | None = None


@dataclass
class SimularSensor:
    fonte: FonteSerie
    envio: EnvioLeituras
    envio_eventos: EnvioEventos | None = None

    def executar(self, pedido: PedidoSimulacao) -> RelatorioSimulacao:
        serie = self.fonte.carregar(pedido.equipamento, pedido.inicio_fonte, pedido.duracao)
        if pedido.reiniciar_em is not None:
            serie = serie.reiniciada_em(pedido.reiniciar_em)
        passo = pedido.config.passo
        if passo != serie.passo:
            raise ErroSimulador("passo do dispositivo deve ser igual ao passo da serie")
        for janela in (*pedido.cenario.janelas_wifi, *pedido.cenario.janelas_energia):
            if janela.fim - janela.inicio < passo:
                raise ErroSimulador("janela de falha menor que um passo de amostragem")
        dispositivo = DispositivoSimulado(pedido.config, pedido.cenario, serie.inicio)
        fim_total = max(serie.fim, pedido.cenario.fim() or serie.fim) + passo
        confirmadas: set[int] = set()
        lotes_ok: list[str] = []
        tentados = falhos = 0
        k = 0
        t = serie.inicio
        while t < fim_total:
            dispositivo.avancar(t, serie.medidas_em(k))
            for lote in dispositivo.lotes_pendentes():
                tentados += 1
                if not self.envio.enviar(lote):
                    falhos += 1
                    break
                dispositivo.confirmar(lote)
                confirmadas.update(a.seq for a in lote.amostras)
                lotes_ok.append(lote.id)
            if self.envio_eventos is not None:
                pendentes = dispositivo.eventos_pendentes()
                if pendentes and self.envio_eventos.enviar(pendentes):
                    dispositivo.confirmar_eventos(len(pendentes))
            k += 1
            t = serie.inicio + passo * k
        return RelatorioSimulacao(
            amostras_registradas=dispositivo.amostras_registradas,
            amostras_confirmadas=len(confirmadas),
            amostras_perdidas_overflow=dispositivo.perdidas_por_overflow,
            pendentes_no_fim=dispositivo.pendentes,
            envios_tentados=tentados,
            envios_falhos=falhos,
            eventos=dispositivo.eventos,
            lacunas=dispositivo.lacunas(),
            lotes_confirmados=tuple(lotes_ok),
            eventos_confirmados=len(dispositivo.eventos) - dispositivo.eventos_nao_confirmados if self.envio_eventos else 0,
            eventos_nao_confirmados=dispositivo.eventos_nao_confirmados if self.envio_eventos else 0,
        )


@dataclass(frozen=True)
class ResultadoEmissao:
    comando: ComandoRele
    resposta: RespostaComando


@dataclass
class EmitirComando:
    chaves: ProvedorChaves
    relogio: Relogio
    nonces: GeradorNonce
    envio: EnvioComando

    def assinar(
        self,
        device_id: str,
        empresa_id: str,
        equipamento_id: str,
        acao: Acao,
        validade_s: float = 30.0,
        nonce: str | None = None,
        emitido_em: datetime | None = None,
    ) -> ComandoRele:
        return construir_comando(
            self.chaves.chave(device_id), device_id, empresa_id, equipamento_id, acao,
            nonce if nonce is not None else self.nonces.novo(),
            emitido_em if emitido_em is not None else self.relogio.agora(), validade_s,
        )

    def executar(
        self,
        device_id: str,
        empresa_id: str,
        equipamento_id: str,
        acao: Acao,
        validade_s: float = 30.0,
        nonce: str | None = None,
        emitido_em: datetime | None = None,
        origem: str = "simulador",
        regra_id: str | None = None,
    ) -> ResultadoEmissao:
        comando = self.assinar(device_id, empresa_id, equipamento_id, acao, validade_s, nonce, emitido_em)
        return ResultadoEmissao(comando, self.envio.enviar(comando, equipamento_id, origem, regra_id))
