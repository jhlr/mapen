import { requisitar, type Resposta } from "./cliente";
import type {
  Configuracao, DesligamentoIn, DesligamentoOut, Equipamento, EquipamentoIn, Regra, RegraIn,
} from "./tipos";

export const criarEquipamento = (corpo: EquipamentoIn): Promise<Resposta<Equipamento>> =>
  requisitar("POST", "/equipamentos", { corpo });

export const criarRegra = (corpo: RegraIn): Promise<Resposta<Regra>> => requisitar("POST", "/regras", { corpo });

export const alterarRegra = (regraId: string, ativo: boolean): Promise<Resposta<{ ativo: boolean }>> =>
  requisitar("PATCH", `/regras/${encodeURIComponent(regraId)}`, { corpo: { ativo } });

/** O PUT grava o evento `configuracao_alterada` com o nome do principal da chave. */
export const alterarConfiguracao = (habilitado: boolean): Promise<Resposta<Configuracao>> =>
  requisitar("PUT", "/configuracao", { corpo: { desligamento_remoto_habilitado: habilitado } });

/**
 * A API responde 200 (aceito), 403 (rejeitado) ou 404 (equipamento desconhecido) com o mesmo corpo
 * DesligamentoOut. 422 e 401 vem como {detail} e sao tratados como erro.
 */
export async function solicitarDesligamento(corpo: DesligamentoIn): Promise<Resposta<DesligamentoOut>> {
  const r = await requisitar<DesligamentoOut | { detail: string }>("POST", "/desligamentos", {
    corpo,
    aceitar: [403, 404],
  });
  if (!r.ok) return r;
  if ("aceito" in r.dados) return { ok: true, status: r.status, dados: r.dados };
  return { ok: false, status: r.status, erro: r.dados.detail };
}
