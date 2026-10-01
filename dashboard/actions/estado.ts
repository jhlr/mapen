import type { DesligamentoOut } from "../lib/api";

/** `valores` devolve o que foi enviado quando a API recusa: o React limpa o form apos a acao. */
export type EstadoForm = { ok: boolean; mensagem: string; valores: Record<string, string> } | null;
export type EstadoDesligamento =
  | { tipo: "erro"; mensagem: string }
  | { tipo: "resposta"; status: number; resposta: DesligamentoOut; equipamento: string; acao: string }
  | null;
