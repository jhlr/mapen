"use server";

import { revalidatePath } from "next/cache";
import { solicitarDesligamento, type Acao } from "../lib/api";
import type { EstadoDesligamento } from "./estado";

const texto = (f: FormData, k: string): string => String(f.get(k) ?? "").trim();

export async function acaoDesligar(_: EstadoDesligamento, f: FormData): Promise<EstadoDesligamento> {
  const acao: Acao = texto(f, "acao") === "ligar" ? "ligar" : "desligar";
  const validade = texto(f, "validade");
  if (validade === "") return { tipo: "erro", mensagem: "Informe a validade do comando (UTC)." };
  // datetime-local não tem fuso; o campo e rotulado UTC e a API exige fuso explicito.
  const iso = /Z|[+-]\d{2}:\d{2}$/.test(validade) ? validade : `${validade.length === 16 ? `${validade}:00` : validade}Z`;
  const equipamento = texto(f, "equipamento_id");
  const autorizado = texto(f, "autorizado_por");
  const r = await solicitarDesligamento(texto(f, "empresa"), {
    equipamento_id: equipamento,
    comando: {
      device_id: texto(f, "device_id"),
      acao,
      nonce: texto(f, "nonce"),
      validade: iso,
      assinatura: texto(f, "assinatura"),
    },
    autorizado_por: autorizado === "" ? null : autorizado,
    origem: "dashboard",
    regra_id: texto(f, "regra_id") || null,
  });
  if (!r.ok) return { tipo: "erro", mensagem: `A API recusou a requisição (HTTP ${r.status}): ${r.erro}` };
  revalidatePath("/desligamento");
  revalidatePath("/eventos");
  return { tipo: "resposta", status: r.status, resposta: r.dados, equipamento, acao };
}
