"use server";

import { revalidatePath } from "next/cache";
import { alterarRegra, criarEquipamento, criarRegra } from "../lib/api";
import type { EstadoForm } from "./estado";

const texto = (f: FormData, k: string): string => String(f.get(k) ?? "").trim();
/** Ecoa os campos de texto/checkbox enviados, para repovoar o form quando a API recusa. */
const eco = (f: FormData): Record<string, string> =>
  Object.fromEntries([...f.entries()].filter(([k, v]) => typeof v === "string" && !k.startsWith("$")).map(([k, v]) => [k, String(v)]));

export async function acaoCriarEquipamento(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  const empresa = texto(f, "empresa");
  const r = await criarEquipamento(empresa, {
    sensor_id: texto(f, "sensor_id"),
    nome: texto(f, "nome"),
    critico: f.get("critico") === "on",
  });
  if (!r.ok) return { ok: false, mensagem: `A API recusou (HTTP ${r.status}): ${r.erro}`, valores: eco(f) };
  revalidatePath("/cadastro");
  return {
    ok: true,
    valores: {},
    mensagem: `Equipamento criado (HTTP ${r.status}): ${r.dados.id}, crítico = ${r.dados.critico ? "sim" : "não"}.`,
  };
}

export async function acaoCriarRegra(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  const empresa = texto(f, "empresa");
  const r = await criarRegra(empresa, {
    equipamento_id: texto(f, "equipamento_id"),
    cron: texto(f, "cron"),
    ativo: f.get("ativo") === "on",
    autorizado_por: texto(f, "autorizado_por"),
  });
  if (!r.ok) return { ok: false, mensagem: `A API recusou (HTTP ${r.status}): ${r.erro}`, valores: eco(f) };
  revalidatePath("/cadastro");
  return {
    ok: true,
    valores: {},
    mensagem: `Regra criada (HTTP ${r.status}): ${r.dados.id}, ${r.dados.ativo ? "ativa" : "inativa"}, autorizada por ${r.dados.autorizado_por}.`,
  };
}

export async function acaoAlterarRegra(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  const r = await alterarRegra(texto(f, "empresa"), texto(f, "regra_id"), f.get("ativo") === "true");
  if (!r.ok) return { ok: false, mensagem: `A API recusou (HTTP ${r.status}): ${r.erro}`, valores: eco(f) };
  revalidatePath("/cadastro");
  return { ok: true, mensagem: r.dados.ativo ? "Regra ativada." : "Regra desativada.", valores: {} };
}
