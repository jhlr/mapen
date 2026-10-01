import type { Evento } from "../api";

export const MOTIVOS: Record<string, string> = {
  assinatura_invalida: "Assinatura HMAC inválida (ou sensor sem chave provisionada na API).",
  validade_vencida: "O comando passou da validade.",
  nonce_repetido: "Esse nonce já foi usado; cada comando precisa de um nonce novo.",
  desligamento_remoto_desabilitado:
    "O desligamento remoto está desativado na API (modo só recomendação). Nada foi enviado ao relé.",
  equipamento_critico: "Equipamento marcado como crítico: nunca é desligado remotamente.",
  sem_autorizacao: "Falta o campo 'autorizado por': todo desligamento precisa de uma pessoa responsável.",
  dispositivo_divergente: "O device_id do comando não é o sensor deste equipamento.",
};
export const MOTIVO_MODO_RECOMENDACAO = "desligamento_remoto_desabilitado";
export const explicarMotivo = (m: string): string => MOTIVOS[m] ?? m;

export type ModoRemoto = "recomendacao" | "habilitado" | "desconhecido";

/**
 * A API nao expoe a flag `desligamento_remoto_habilitado`; o modo e inferido do evento de
 * desligamento mais recente (a flag e a ultima regra avaliada, entao essa rejeicao a identifica).
 * `eventos` vem do mais novo para o mais antigo.
 */
export function inferirModo(eventos: Evento[]): ModoRemoto {
  for (const e of eventos) {
    if (e.tipo === "desligamento_executado") return "habilitado";
    if (e.tipo === "comando_rejeitado" && e.payload.motivo === MOTIVO_MODO_RECOMENDACAO) return "recomendacao";
  }
  return "desconhecido";
}
