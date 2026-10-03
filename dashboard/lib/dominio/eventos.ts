// View-model dos eventos que o proprio dispositivo mede (relogio do dispositivo): funcoes puras, sem fetch nem React.
import type { Evento } from "../api/tipos";
import { SIM_NAO, dataHora, num } from "./formatacao";

export const TIPOS_DISPOSITIVO: readonly string[] = ["ultimo_suspiro", "queda_energia", "falha_conexao"];

/** "900,45 s" ate 2 min; depois "15 min 0 s". Nunca inventa duracao: ausente vira texto explicito. */
export function duracao(segundos: number): string {
  if (segundos < 120) return `${num(segundos, 2)} s`;
  const minutos = Math.floor(segundos / 60);
  return `${num(minutos, 0)} min ${num(Math.round(segundos - minutos * 60), 0)} s`;
}

/** Detalhe de um evento de dispositivo a partir do payload; `null` para eventos que nao sao do dispositivo. */
export function detalheDispositivo(e: Evento): string | null {
  if (!TIPOS_DISPOSITIVO.includes(e.tipo)) return null;
  const p = e.payload;
  const partes: string[] = [];
  if (e.tipo === "ultimo_suspiro") {
    partes.push("início da queda gravado pelo relógio do dispositivo");
  } else if (p.duracao_s !== undefined) {
    partes.push(`duração ${duracao(Number(p.duracao_s))} (relógio do dispositivo)`);
  } else {
    partes.push("duração desconhecida: o relógio do dispositivo não sobreviveu");
  }
  if (e.tipo === "queda_energia" && p.bateria_esgotada !== undefined) partes.push(`bateria esgotada: ${SIM_NAO(p.bateria_esgotada === "true")}`);
  if (p.recebido_em !== undefined) partes.push(`recebido pela plataforma em ${dataHora(p.recebido_em)}`);
  return partes.join("; ");
}
