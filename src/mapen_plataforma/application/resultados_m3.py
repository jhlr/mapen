"""Casos de uso de consulta dos resultados do M3. Somente leitura, sempre por empresa."""

from __future__ import annotations

from dataclasses import dataclass

from mapen_plataforma.application.portas import ResultadosM3Repositorio
from mapen_plataforma.domain.entidades import ErroDominio
from mapen_plataforma.domain.resultados_m3 import (
    AlertaM3,
    AlertasM3,
    AvisoD7,
    ComparacaoEquipamento,
    EconomiaM3,
    FiltroAlertas,
    ResumoM3,
    Veredito,
    avaliar_aviso_d7,
    comparar,
    equipamentos_com_baseline_fraca,
    filtrar_alertas,
    veredito,
)

LIMITE_ALERTAS_MAX = 500
LIMITE_ALERTAS_PADRAO = 100


@dataclass(frozen=True)
class ResumoConsultado:
    """`resumo` e `None` quando a empresa nao tem resultados do M3."""

    resumo: ResumoM3 | None
    aviso_d7: AvisoD7 | None
    equipamentos_baseline_fraca: tuple[str, ...]


@dataclass(frozen=True)
class PaginaAlertas:
    """`base` e `None` quando a empresa nao tem resultados do M3 (pagina vazia)."""

    base: AlertasM3 | None
    total: int
    limite: int
    offset: int
    itens: tuple[AlertaM3, ...]


@dataclass(frozen=True)
class EconomiaConsultada:
    """`economia` e `None` quando a empresa nao tem resultados do M3."""

    economia: EconomiaM3 | None
    comparacoes: tuple[ComparacaoEquipamento, ...]
    veredito: Veredito | None


class ConsultarResumoM3:
    def __init__(self, repo: ResultadosM3Repositorio) -> None:
        self._repo = repo

    def executar(self, empresa_id: str) -> ResumoConsultado:
        resumo = self._repo.resumo(empresa_id)
        alertas, economia = self._repo.alertas(empresa_id), self._repo.economia(empresa_id)
        if resumo is None or alertas is None or economia is None:
            return ResumoConsultado(None, None, ())
        return ResumoConsultado(
            resumo, avaliar_aviso_d7(resumo.shap), tuple(equipamentos_com_baseline_fraca(alertas, economia))
        )


class ListarAlertasM3:
    def __init__(self, repo: ResultadosM3Repositorio) -> None:
        self._repo = repo

    def executar(self, empresa_id: str, filtro: FiltroAlertas, limite: int, offset: int) -> PaginaAlertas:
        if not 1 <= limite <= LIMITE_ALERTAS_MAX:
            raise ErroDominio(f"limite deve estar entre 1 e {LIMITE_ALERTAS_MAX}")
        if offset < 0:
            raise ErroDominio("offset deve ser >= 0")
        if filtro.de is not None and filtro.ate is not None and filtro.de >= filtro.ate:
            raise ErroDominio("de deve ser anterior a ate")
        base = self._repo.alertas(empresa_id)
        if base is None:
            return PaginaAlertas(None, 0, limite, offset, ())
        achados = filtrar_alertas(base.alertas, filtro)
        return PaginaAlertas(base, len(achados), limite, offset, tuple(achados[offset : offset + limite]))


class ConsultarEconomiaM3:
    def __init__(self, repo: ResultadosM3Repositorio) -> None:
        self._repo = repo

    def executar(self, empresa_id: str) -> EconomiaConsultada:
        economia = self._repo.economia(empresa_id)
        if economia is None:
            return EconomiaConsultada(None, (), None)
        return EconomiaConsultada(economia, tuple(comparar(economia)), veredito(economia))
