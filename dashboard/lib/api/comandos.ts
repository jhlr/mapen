import { requisitar, type Resposta } from "./cliente";
import type { DesligamentoIn, DesligamentoOut, Equipamento, EquipamentoIn, Regra, RegraIn } from "./tipos";

export const criarEquipamento = (empresa: string, corpo: EquipamentoIn): Promise<Resposta<Equipamento>> =>
  requisitar("POST", "/equipamentos", empresa, { corpo });

export const criarRegra = (empresa: string, corpo: RegraIn): Promise<Resposta<Regra>> =>
  requisitar("POST", "/regras", empresa, { corpo });

export const alterarRegra = (empresa: string, regraId: string, ativo: boolean): Promise<Resposta<{ ativo: boolean }>> =>
  requisitar("PATCH", `/regras/${encodeURIComponent(regraId)}`, empresa, { corpo: { ativo } });

/**
 * A API responde 200 (aceito) ou 403 (rejeitado) com o mesmo corpo. Outro 403 (empresa desconhecida)
 * vem como {detail}; ele e tratado como erro.
 */
export async function solicitarDesligamento(
  empresa: string,
  corpo: DesligamentoIn,
): Promise<Resposta<DesligamentoOut>> {
  const r = await requisitar<DesligamentoOut | { detail: string }>("POST", "/desligamentos", empresa, {
    corpo,
    aceitar: [403],
  });
  if (!r.ok) return r;
  if ("aceito" in r.dados) return { ok: true, status: r.status, dados: r.dados };
  return { ok: false, status: r.status, erro: r.dados.detail };
}
