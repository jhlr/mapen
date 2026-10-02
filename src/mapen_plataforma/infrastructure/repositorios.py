"""Repositorios DuckDB. Toda consulta e filtrada por empresa (isolamento de tenant)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from mapen_plataforma.application.portas import ConsumoEquipamento, ConsumoHora, CredencialDispositivo
from mapen_plataforma.domain.comando import ConfiguracaoSeguranca
from mapen_plataforma.domain.credenciais import Principal
from mapen_plataforma.domain.tempo import de_local_ingenuo, para_local_ingenuo
from mapen_plataforma.domain.entidades import (
    Empresa,
    Equipamento,
    Evento,
    Leitura,
    RegraDesligamento,
    Sensor,
    TipoEvento,
    Unidade,
)
from mapen_plataforma.infrastructure.banco import BancoDuckDB


def _naive_utc(ts: datetime) -> datetime:
    return ts.astimezone(UTC).replace(tzinfo=None) if ts.tzinfo else ts


def _aware_utc(valor: object) -> datetime:
    assert isinstance(valor, datetime)
    return valor.replace(tzinfo=UTC)


def _hora_local(valor: object) -> datetime:
    assert isinstance(valor, datetime)
    return de_local_ingenuo(valor)


class EmpresaDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, empresa: Empresa) -> None:
        self._b.executar("INSERT INTO empresa VALUES (?, ?)", [empresa.id, empresa.nome])

    def obter(self, empresa_id: str) -> Empresa | None:
        linhas = self._b.consultar("SELECT id, nome FROM empresa WHERE id = ?", [empresa_id])
        return Empresa(str(linhas[0][0]), str(linhas[0][1])) if linhas else None


class UnidadeDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, unidade: Unidade) -> None:
        self._b.executar(
            "INSERT INTO unidade VALUES (?, ?, ?)", [unidade.id, unidade.empresa_id, unidade.nome]
        )

    def listar(self, empresa_id: str) -> list[Unidade]:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, nome FROM unidade WHERE empresa_id = ? ORDER BY nome, id", [empresa_id]
        )
        return [Unidade(str(a), str(b), str(c)) for a, b, c in linhas]

    def obter(self, empresa_id: str, unidade_id: str) -> Unidade | None:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, nome FROM unidade WHERE empresa_id = ? AND id = ?", [empresa_id, unidade_id]
        )
        return Unidade(str(linhas[0][0]), str(linhas[0][1]), str(linhas[0][2])) if linhas else None


class SensorDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, sensor: Sensor) -> None:
        self._b.executar(
            "INSERT INTO sensor VALUES (?, ?, ?, ?)",
            [sensor.id, sensor.empresa_id, sensor.unidade_id, sensor.nome],
        )

    def listar(self, empresa_id: str) -> list[Sensor]:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, unidade_id, nome FROM sensor WHERE empresa_id = ? ORDER BY id",
            [empresa_id],
        )
        return [Sensor(str(a), str(b), str(c), str(d)) for a, b, c, d in linhas]

    def obter(self, empresa_id: str, sensor_id: str) -> Sensor | None:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, unidade_id, nome FROM sensor WHERE empresa_id = ? AND id = ?",
            [empresa_id, sensor_id],
        )
        if not linhas:
            return None
        a, b, c, d = linhas[0]
        return Sensor(str(a), str(b), str(c), str(d))


class EquipamentoDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, equipamento: Equipamento) -> None:
        self._b.executar(
            "INSERT INTO equipamento VALUES (?, ?, ?, ?, ?)",
            [equipamento.id, equipamento.empresa_id, equipamento.sensor_id, equipamento.nome, equipamento.critico],
        )

    def listar(self, empresa_id: str) -> list[Equipamento]:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, sensor_id, nome, critico FROM equipamento "
            "WHERE empresa_id = ? ORDER BY sensor_id, nome",
            [empresa_id],
        )
        return [Equipamento(str(a), str(b), str(c), str(d), bool(e)) for a, b, c, d, e in linhas]

    def obter(self, empresa_id: str, equipamento_id: str) -> Equipamento | None:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, sensor_id, nome, critico FROM equipamento WHERE empresa_id = ? AND id = ?",
            [empresa_id, equipamento_id],
        )
        if not linhas:
            return None
        a, b, c, d, e = linhas[0]
        return Equipamento(str(a), str(b), str(c), str(d), bool(e))


class RegraDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, regra: RegraDesligamento) -> None:
        self._b.executar(
            "INSERT INTO regra_desligamento VALUES (?, ?, ?, ?, ?, ?, ?)",
            [regra.id, regra.empresa_id, regra.equipamento_id, regra.cron, regra.ativo,
             regra.autorizado_por, _naive_utc(regra.criado_em)],
        )

    def listar(self, empresa_id: str) -> list[RegraDesligamento]:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, equipamento_id, cron, ativo, autorizado_por, criado_em "
            "FROM regra_desligamento WHERE empresa_id = ? ORDER BY criado_em, id",
            [empresa_id],
        )
        return [
            RegraDesligamento(str(a), str(b), str(c), str(d), bool(e), str(f), _aware_utc(g))
            for a, b, c, d, e, f, g in linhas
        ]

    def obter(self, empresa_id: str, regra_id: str) -> RegraDesligamento | None:
        linhas = self._b.consultar(
            "SELECT id, empresa_id, equipamento_id, cron, ativo, autorizado_por, criado_em "
            "FROM regra_desligamento WHERE empresa_id = ? AND id = ?",
            [empresa_id, regra_id],
        )
        if not linhas:
            return None
        a, b, c, d, e, f, g = linhas[0]
        return RegraDesligamento(str(a), str(b), str(c), str(d), bool(e), str(f), _aware_utc(g))

    def definir_ativo(self, empresa_id: str, regra_id: str, ativo: bool) -> bool:
        with self._b.trava:
            if self.obter(empresa_id, regra_id) is None:
                return False
            self._b.executar(
                "UPDATE regra_desligamento SET ativo = ? WHERE id = ? AND empresa_id = ?",
                [ativo, regra_id, empresa_id],
            )
            return True


class EventoDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, evento: Evento) -> None:
        self._b.executar(
            "INSERT INTO evento VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [evento.id, _naive_utc(evento.ts), evento.tipo.value, evento.empresa_id, evento.sensor_id,
             evento.equipamento_id, evento.origem, evento.regra_id, evento.autorizado_por,
             json.dumps(evento.payload, sort_keys=True)],
        )

    def adicionar_se_novo(self, evento: Evento) -> bool:
        with self._b.trava:
            resultado = self._b.conexao.execute(
                "INSERT INTO evento VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [evento.id, _naive_utc(evento.ts), evento.tipo.value, evento.empresa_id, evento.sensor_id,
                 evento.equipamento_id, evento.origem, evento.regra_id, evento.autorizado_por,
                 json.dumps(evento.payload, sort_keys=True)],
            ).fetchall()
        return int(str(resultado[0][0])) == 1

    def listar(self, empresa_id: str, limite: int) -> list[Evento]:
        linhas = self._b.consultar(
            "SELECT id, ts, tipo, empresa_id, sensor_id, equipamento_id, origem, regra_id, "
            "autorizado_por, payload FROM evento WHERE empresa_id = ? ORDER BY ts DESC, rowid DESC LIMIT ?",
            [empresa_id, limite],
        )
        return [
            Evento(
                str(i), _aware_utc(ts), TipoEvento(str(tipo)), str(emp),
                None if sid is None else str(sid), None if eid is None else str(eid),
                str(origem), None if rid is None else str(rid), None if aut is None else str(aut),
                {str(k): str(v) for k, v in json.loads(str(payload)).items()},
            )
            for i, ts, tipo, emp, sid, eid, origem, rid, aut, payload in linhas
        ]


class NonceDuckDB:
    """Nonces ja vistos por dispositivo. A chave primaria + ON CONFLICT DO NOTHING decide, atomicamente, quem usou primeiro."""

    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def registrar(self, device_id: str, nonce: str, expira_em: datetime) -> bool:
        with self._b.trava:
            resultado = self._b.conexao.execute(
                "INSERT INTO nonce (device_id, nonce, expira_em) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                [device_id, nonce, _naive_utc(expira_em)],
            ).fetchall()
        return int(str(resultado[0][0])) == 1

    def podar(self, agora: datetime) -> int:
        with self._b.trava:
            resultado = self._b.conexao.execute(
                "DELETE FROM nonce WHERE expira_em < ?", [_naive_utc(agora)]
            ).fetchall()
        return int(str(resultado[0][0]))


class CredenciaisEmpresaDuckDB:
    """Chaves de API por empresa e principal; so o hash SHA-256 fica no banco."""

    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def definir(self, empresa_id: str, principal: str, hash_chave: str) -> None:
        with self._b.trava:
            self._b.executar(
                "DELETE FROM credencial_empresa WHERE empresa_id = ? AND principal = ?", [empresa_id, principal]
            )
            self._b.executar(
                "INSERT INTO credencial_empresa (hash_chave, empresa_id, principal) VALUES (?, ?, ?)",
                [hash_chave, empresa_id, principal],
            )

    def buscar(self, hash_chave: str) -> Principal | None:
        linhas = self._b.consultar(
            "SELECT empresa_id, principal FROM credencial_empresa WHERE hash_chave = ?", [hash_chave]
        )
        return Principal(str(linhas[0][0]), str(linhas[0][1])) if linhas else None


class CredenciaisDispositivoDuckDB:
    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def definir(self, credencial: CredencialDispositivo) -> None:
        with self._b.trava:
            self._b.executar("DELETE FROM credencial_dispositivo WHERE device_id = ?", [credencial.device_id])
            self._b.executar(
                "INSERT INTO credencial_dispositivo (device_id, empresa_id, token_hash, sal) VALUES (?, ?, ?, ?)",
                [credencial.device_id, credencial.empresa_id, credencial.token_hash, credencial.sal],
            )

    def obter(self, device_id: str) -> CredencialDispositivo | None:
        linhas = self._b.consultar(
            "SELECT device_id, empresa_id, token_hash, sal FROM credencial_dispositivo WHERE device_id = ?",
            [device_id],
        )
        if not linhas:
            return None
        a, b, c, d = linhas[0]
        return CredencialDispositivo(str(a), str(b), str(c), str(d))


class ConfiguracaoDuckDB:
    """Flag por empresa; sem linha, vale o padrao do dominio (desligado)."""

    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def obter(self, empresa_id: str) -> ConfiguracaoSeguranca:
        linhas = self._b.consultar(
            "SELECT desligamento_remoto_habilitado FROM configuracao_empresa WHERE empresa_id = ?", [empresa_id]
        )
        return ConfiguracaoSeguranca(bool(linhas[0][0])) if linhas else ConfiguracaoSeguranca()

    def definir(self, empresa_id: str, config: ConfiguracaoSeguranca) -> None:
        with self._b.trava:
            self._b.executar("DELETE FROM configuracao_empresa WHERE empresa_id = ?", [empresa_id])
            self._b.executar(
                "INSERT INTO configuracao_empresa VALUES (?, ?)", [empresa_id, config.desligamento_remoto_habilitado]
            )


class LeituraDuckDB:
    """Adaptador da porta de ingestao sobre a tabela `leitura` do M1."""

    def __init__(self, banco: BancoDuckDB) -> None:
        self._b = banco

    def adicionar(self, leituras: list[Leitura]) -> int:
        if not leituras:
            return 0
        tabela = pd.DataFrame(
            {
                "sensor_id": [x.sensor_id for x in leituras],
                "equipamento_id": [x.equipamento_nome for x in leituras],
                "ts": pd.to_datetime([para_local_ingenuo(x.ts, "ts") for x in leituras]),
                "potencia_w": pd.array([x.potencia_w for x in leituras], dtype="Float64"),
                "tensao_v": pd.array([x.tensao_v for x in leituras], dtype="Float64"),
                "kwh": pd.array([x.kwh for x in leituras], dtype="Float64"),
                "ausente": [x.ausente for x in leituras],
            }
        )
        tabela = tabela.drop_duplicates(["sensor_id", "equipamento_id", "ts"], keep="first")
        with self._b.trava:
            antes = self._contar()
            self._b.conexao.register("lote_leitura", tabela)
            try:
                self._b.conexao.execute(
                    "INSERT INTO leitura SELECT l.* FROM lote_leitura l WHERE NOT EXISTS ("
                    "SELECT 1 FROM leitura x WHERE x.sensor_id = l.sensor_id "
                    "AND x.equipamento_id = l.equipamento_id AND x.ts = l.ts)"
                )
            finally:
                self._b.conexao.unregister("lote_leitura")
            return self._contar() - antes

    def _contar(self) -> int:
        total = self._b.consultar("SELECT count(*) FROM leitura")[0][0]
        assert isinstance(total, int)
        return total

    def ultimo_ts(self, sensor_id: str) -> datetime | None:
        linhas = self._b.consultar(
            "SELECT max(ts) FROM leitura WHERE sensor_id = ? AND NOT ausente", [sensor_id]
        )
        valor = linhas[0][0]
        return de_local_ingenuo(valor) if isinstance(valor, datetime) else None

    def consumo_por_equipamento(
        self, sensor_id: str, inicio: datetime, fim: datetime
    ) -> list[ConsumoEquipamento]:
        linhas = self._b.consultar(
            "SELECT equipamento_id, coalesce(sum(kwh), 0) FROM leitura "
            "WHERE sensor_id = ? AND ts >= ? AND ts < ? GROUP BY equipamento_id ORDER BY equipamento_id",
            [sensor_id, para_local_ingenuo(inicio, "inicio"), para_local_ingenuo(fim, "fim")],
        )
        return [ConsumoEquipamento(str(n), float(str(k))) for n, k in linhas]

    def consumo_horario(self, sensor_id: str, inicio: datetime, fim: datetime) -> list[ConsumoHora]:
        linhas = self._b.consultar(
            "SELECT date_trunc('hour', ts) AS hora, sum(kwh) FROM leitura "
            "WHERE sensor_id = ? AND ts >= ? AND ts < ? AND NOT ausente GROUP BY hora "
            "HAVING sum(kwh) IS NOT NULL ORDER BY hora",
            [sensor_id, para_local_ingenuo(inicio, "inicio"), para_local_ingenuo(fim, "fim")],
        )
        return [ConsumoHora(_hora_local(hora), float(str(kwh))) for hora, kwh in linhas]

    def potencia_em(self, sensor_id: str, ts: datetime) -> float:
        linhas = self._b.consultar(
            "SELECT coalesce(sum(potencia_w), 0) FROM leitura WHERE sensor_id = ? AND ts = ?",
            [sensor_id, para_local_ingenuo(ts, "ts")],
        )
        return float(str(linhas[0][0]))
