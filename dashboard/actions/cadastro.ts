"use server";

import { revalidatePath } from "next/cache";
import { alterarRegra, criarEquipamento, criarRegra } from "../lib/api";
import type { EstadoForm } from "./estado";

const texto = (f: FormData, k: string): string => String(f.get(k) ?? "").trim();
/** Ecoa os campos de texto/checkbox enviados, para repovoar o form quando a API recusa. */
const eco = (f: FormData): Record<string, string> =>
  Object.fromEntries([...f.entries()].filter(([k, v]) => typeof v === "string" && !k.startsWith("$")).map(([k, v]) => [k, String(v)]));
const recusa = (f: FormData, status: number, erro: string): EstadoForm => ({
  ok: false,
  mensagem: status === 401 ? `Chave de API ausente ou recusada (HTTP 401): ${erro}` : `A API recusou (HTTP ${status}): ${erro}`,
  valores: eco(f),
});

export async function acaoCriarEquipamento(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  // critico sempre vai explicito (true ou false): a API nao tem padrao e falha fechada.
  const r = await criarEquipamento({
    sensor_id: texto(f, "sensor_id"),
    nome: texto(f, "nome"),
    critico: f.get("critico") === "on",
  });
  if (!r.ok) return recusa(f, r.status, r.erro);
  revalidatePath("/cadastro");
  return {
    ok: true,
    valores: {},
    mensagem: `Equipamento criado (HTTP ${r.status}): ${r.dados.id}, crítico = ${r.dados.critico ? "sim" : "não"}.`,
  };
}

export async function acaoCriarRegra(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  const r = await criarRegra({
    equipamento_id: texto(f, "equipamento_id"),
    cron: texto(f, "cron"),
    ativo: f.get("ativo") === "on",
  });
  if (!r.ok) return recusa(f, r.status, r.erro);
  revalidatePath("/cadastro");
  return {
    ok: true,
    valores: {},
    mensagem: `Regra criada (HTTP ${r.status}): ${r.dados.id}, ${r.dados.ativo ? "ativa" : "inativa"}, autorizada por ${r.dados.autorizado_por}.`,
  };
}

export async function acaoAlterarRegra(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  const r = await alterarRegra(texto(f, "regra_id"), f.get("ativo") === "true");
  if (!r.ok) return recusa(f, r.status, r.erro);
  revalidatePath("/cadastro");
  return { ok: true, mensagem: r.dados.ativo ? "Regra ativada." : "Regra desativada.", valores: {} };
}
