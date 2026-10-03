// Fuso da instalacao (America/Recife). Toda data enviada a API carrega o offset; a API recusa data sem fuso.
const ZONA = "America/Recife";
const fmt = new Intl.DateTimeFormat("en-US", { timeZone: ZONA, timeZoneName: "longOffset" });

/** Offset de Recife, em minutos, no instante `ms` (epoch ms). */
function offsetMin(ms: number): number {
  const nome = fmt.formatToParts(ms).find((p) => p.type === "timeZoneName")?.value ?? "GMT";
  const m = /GMT([+-])(\d{2}):(\d{2})/.exec(nome);
  if (m === null) return 0;
  return (m[1] === "-" ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]));
}

const dois = (n: number): string => String(n).padStart(2, "0");

/** "AAAA-MM-DDTHH:MM[:SS]" lido como horario de parede de Recife -> epoch ms. */
export function instanteDeRecife(naivo: string): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(naivo);
  if (m === null) return Number.NaN;
  const [a, mes, d, h, mi, s] = m.slice(1).map((x) => Number(x ?? 0)) as [number, number, number, number, number, number];
  const parede = Date.UTC(a, mes - 1, d, h, mi, s);
  const primeiro = parede - offsetMin(parede) * 60_000;
  return parede - offsetMin(primeiro) * 60_000;
}

/** epoch ms -> "AAAA-MM-DDTHH:MM:SS-03:00" (offset de Recife naquele instante). */
export function isoRecife(ms: number): string {
  const off = offsetMin(ms);
  const sinal = off < 0 ? "-" : "+";
  const abs = Math.abs(off);
  return `${new Date(ms + off * 60_000).toISOString().slice(0, 19)}${sinal}${dois(Math.floor(abs / 60))}:${dois(abs % 60)}`;
}

/** epoch ms -> "AAAA-MM-DDTHH:MM:SS" em horario de parede de Recife (valor de input datetime-local). */
export const naivoRecife = (ms: number): string => new Date(ms + offsetMin(ms) * 60_000).toISOString().slice(0, 19);

/** Horario de parede de Recife (ou ja com offset) -> ISO com offset. Devolve "" se nao der para ler. */
export function comFuso(valor: string): string {
  if (/(Z|[+-]\d{2}:\d{2})$/.test(valor)) return valor;
  const ms = instanteDeRecife(valor);
  return Number.isNaN(ms) ? "" : isoRecife(ms);
}

/** Epoch em segundos (o que entra na mensagem assinada) de um horario de parede de Recife. */
export const epochSegundos = (naivo: string): number => Math.floor(instanteDeRecife(naivo) / 1000);

/** Soma `dias` a uma data AAAA-MM-DD (calendario puro, sem fuso). */
export function somarDias(dia: string, dias: number): string {
  const [a, m, d] = dia.split("-").map(Number);
  return new Date(Date.UTC(a ?? 1970, (m ?? 1) - 1, (d ?? 1) + dias)).toISOString().slice(0, 10);
}

/** Instantes (com offset) de meia-noite de dois dias de calendario de Recife: [inicio, fimExclusivo). */
export const intervaloDeDias = (primeiroDia: string, ultimoDia: string): { inicio: string; fim: string } => ({
  inicio: comFuso(`${primeiroDia}T00:00:00`),
  fim: comFuso(`${somarDias(ultimoDia, 1)}T00:00:00`),
});
