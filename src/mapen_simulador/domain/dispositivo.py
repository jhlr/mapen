"""Dispositivo simulado: o comportamento de firmware exigido do hardware proprio do M2.

Registra com o proprio relogio (RTC), guarda num buffer circular, sobrevive a queda de Wi-Fi e de
energia dentro da autonomia da bateria, grava o inicio da queda (ultimo suspiro) e envia em lote
quando volta a conexao. Nao faz I/O: o tempo real chega por `avancar`, o envio e feito por quem chama.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from mapen_simulador.domain.amostras import Amostra, LoteLeituras
from mapen_simulador.domain.carga import Medida
from mapen_simulador.domain.cenario import Cenario, Conectividade, Janela
from mapen_simulador.domain.erros import ErroSimulador
from mapen_simulador.domain.eventos import EventoDispositivo, TipoEvento
from mapen_simulador.domain.relatorio import Lacuna, calcular_lacunas
from mapen_simulador.domain.relogio import RelogioDispositivo


@dataclass(frozen=True)
class ConfigDispositivo:
    device_id: str
    passo: timedelta = timedelta(minutes=1)
    capacidade_buffer: int = 10_000
    tamanho_lote: int = 500
    deriva_ppm: float = 0.0
    rtc_sobrevive_a_bateria_zerada: bool = True

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ErroSimulador("device_id vazio")
        if self.passo <= timedelta(0):
            raise ErroSimulador("passo deve ser positivo")
        if self.capacidade_buffer < 1 or self.tamanho_lote < 1:
            raise ErroSimulador("capacidade do buffer e tamanho do lote devem ser positivos")


class DispositivoSimulado:
    def __init__(self, config: ConfigDispositivo, cenario: Cenario, inicio: datetime) -> None:
        self._cfg = config
        self._cenario = cenario
        self._relogio = RelogioDispositivo(inicio, config.deriva_ppm)
        self._buffer: deque[Amostra] = deque(maxlen=config.capacidade_buffer)
        self._seq = 0
        self._ticks: list[datetime] = []
        self._eventos: list[EventoDispositivo] = []
        self._perdidas = 0
        self._conectividade = Conectividade.ONLINE
        self._bateria = cenario.autonomia
        self._queda: Janela | None = None
        self._wifi: Janela | None = None

    @property
    def conectividade(self) -> Conectividade:
        return self._conectividade

    @property
    def eventos(self) -> tuple[EventoDispositivo, ...]:
        return tuple(self._eventos)

    @property
    def amostras_registradas(self) -> int:
        return self._seq

    @property
    def perdidas_por_overflow(self) -> int:
        return self._perdidas

    @property
    def pendentes(self) -> int:
        return len(self._buffer)

    def lacunas(self) -> tuple[Lacuna, ...]:
        return calcular_lacunas(self._ticks, self._cfg.passo)

    def bateria_restante(self) -> timedelta:
        return self._bateria

    def avancar(self, t: datetime, medidas: Sequence[Medida]) -> None:
        """Um tick do mundo em tempo real `t`; grava `medidas` se o dispositivo estiver energizado."""
        anterior = self._conectividade
        atual = self._cenario.conectividade_em(t)
        self._tratar_energia(anterior, atual, t)
        self._tratar_wifi(atual, t)
        self._conectividade = atual
        if atual is Conectividade.MAINS_DOWN:
            if self._bateria <= timedelta(0):
                return
            self._bateria -= self._cfg.passo
        else:
            self._bateria = self._cenario.autonomia
        if medidas:
            self._registrar(t, medidas)

    def lotes_pendentes(self) -> list[LoteLeituras]:
        """Lotes prontos para enviar (so com conexao), do mais antigo ao mais novo, sem remover do buffer."""
        if self._conectividade is not Conectividade.ONLINE:
            return []
        itens = list(self._buffer)
        n = self._cfg.tamanho_lote
        lotes: list[LoteLeituras] = []
        for i in range(0, len(itens), n):
            fatia = tuple(itens[i : i + n])
            lotes.append(LoteLeituras(f"{self._cfg.device_id}:{fatia[0].seq}-{fatia[-1].seq}", fatia))
        return lotes

    def confirmar(self, lote: LoteLeituras) -> None:
        """So depois da confirmacao do servidor o lote sai do buffer."""
        while self._buffer and self._buffer[0].seq <= lote.seq_ultima:
            self._buffer.popleft()

    def _registrar(self, t: datetime, medidas: Sequence[Medida]) -> None:
        ts = self._relogio.ler(t)
        self._ticks.append(ts)
        horas = self._cfg.passo.total_seconds() / 3600.0
        for m in medidas:
            self._seq += 1
            if len(self._buffer) == self._buffer.maxlen:
                self._perdidas += 1
            self._buffer.append(Amostra(self._seq, ts, m.equipamento, m.potencia_w, m.potencia_w / 1000.0 * horas))

    def _tratar_energia(self, anterior: Conectividade, atual: Conectividade, t: datetime) -> None:
        if atual is Conectividade.MAINS_DOWN and anterior is not Conectividade.MAINS_DOWN:
            janela = self._cenario.janela_energia_em(t)
            assert janela is not None
            self._queda = janela
            self._eventos.append(EventoDispositivo(TipoEvento.ULTIMO_SUSPIRO, self._relogio.ler(janela.inicio)))
        elif anterior is Conectividade.MAINS_DOWN and atual is not Conectividade.MAINS_DOWN:
            assert self._queda is not None
            esgotada = self._bateria <= timedelta(0)
            inicio = self._relogio.ler(self._queda.inicio)
            if esgotada and not self._cfg.rtc_sobrevive_a_bateria_zerada:
                self._eventos.append(EventoDispositivo(TipoEvento.QUEDA_ENERGIA, inicio, None, None, True))
            else:
                fim = self._relogio.ler(self._queda.fim)
                self._eventos.append(
                    EventoDispositivo(TipoEvento.QUEDA_ENERGIA, inicio, fim, (fim - inicio).total_seconds(), esgotada)
                )
            self._queda = None

    def _tratar_wifi(self, atual: Conectividade, t: datetime) -> None:
        if atual is Conectividade.WIFI_DOWN and self._wifi is None:
            self._wifi = self._cenario.janela_wifi_em(t)
        elif atual is Conectividade.MAINS_DOWN and self._wifi is not None:
            self._eventos.append(EventoDispositivo(TipoEvento.FALHA_CONEXAO, self._relogio.ler(self._wifi.inicio)))
            self._wifi = None
        elif atual is Conectividade.ONLINE and self._wifi is not None:
            inicio, fim = self._relogio.ler(self._wifi.inicio), self._relogio.ler(self._wifi.fim)
            self._eventos.append(EventoDispositivo(TipoEvento.FALHA_CONEXAO, inicio, fim, (fim - inicio).total_seconds()))
            self._wifi = None
