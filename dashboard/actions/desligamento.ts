"use server";

import { revalidatePath } from "next/cache";
import { alterarConfiguracao, solicitarDesligamento, type Acao } from "../lib/api";
import { comFuso } from "../lib/dominio/fuso";
import type { EstadoDesligamento, EstadoForm } from "./estado";

const texto = (f: FormData, k: string): string => String(f.get(k) ?? "").trim();

export async function acaoDesligar(_: EstadoDesligamento, f: FormData): Promise<EstadoDesligamento> {
  const acao: Acao = texto(f, "acao") === "ligar" ? "ligar" : "desligar";
  // datetime-local nao tem fuso; os campos sao rotulados Recife e a API exige offset explicito.
  const emitido = comFuso(texto(f, "emitido_em"));
  const validade = comFuso(texto(f, "validade"));
  if (emitido === "" || validade === "") return { tipo: "erro", mensagem: "Informe a emissão e a validade do comando." };
  const equipamento = texto(f, "equipamento_id");
  // Sem autorizado_por: quem autoriza e o principal da chave de API.
  const r = await solicitarDesligamento({
    equipamento_id: equipamento,
    comando: {
      device_id: texto(f, "device_id"),
      acao,
      nonce: texto(f, "nonce"),
      emitido_em: emitido,
      validade,
      assinatura: texto(f, "assinatura"),
    },
    origem: "dashboard",
    regra_id: texto(f, "regra_id") || null,
  });
  if (!r.ok) return { tipo: "erro", mensagem: `A API recusou a requisição (HTTP ${r.status}): ${r.erro}` };
  revalidatePath("/desligamento");
  revalidatePath("/eventos");
  return { tipo: "resposta", status: r.status, resposta: r.dados, equipamento, acao };
}

/** Altera desligamento_remoto_habilitado. A confirmacao em duas etapas fica na tela; a API grava o evento. */
export async function acaoAlterarConfiguracao(_: EstadoForm, f: FormData): Promise<EstadoForm> {
  const habilitar = texto(f, "habilitar") === "true";
  const r = await alterarConfiguracao(habilitar);
  if (!r.ok) {
    return {
      ok: false,
      mensagem: r.status === 401 ? `Chave de API ausente ou recusada (HTTP 401).` : `A API recusou (HTTP ${r.status}): ${r.erro}`,
      valores: {},
    };
  }
  revalidatePath("/desligamento");
  revalidatePath("/eventos");
  return {
    ok: true,
    valores: {},
    mensagem: `Desligamento remoto ${r.dados.desligamento_remoto_habilitado ? "habilitado" : "desabilitado"} (HTTP ${r.status}). Evento configuracao_alterada registrado.`,
  };
}
