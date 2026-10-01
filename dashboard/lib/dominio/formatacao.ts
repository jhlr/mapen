// Funcoes puras de apresentacao (pt-BR).
const brlFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
export const brl = (v: number): string => brlFmt.format(v);

export const num = (v: number, casas = 1): string =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const kwh = (v: number, casas = 1): string => `${num(v, casas)} kWh`;
export const watts = (v: number): string => `${num(v, 0)} W`;
export const pct = (v: number): string => `${num(v, 1)}%`;

/** "2018-08-31T23:59:00" ou ISO com fuso -> "31/08/2018 23:59" (sem converter fuso: so reordena). */
export function dataHora(ts: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(ts);
  return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : ts;
}

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
export const rotuloMes = (ano: number, mes: number): string => `${MESES[mes - 1]} de ${ano}`;

export const SIM_NAO = (v: boolean): string => (v ? "sim" : "não");
