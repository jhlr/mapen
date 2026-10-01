import { rotuloMes } from "./formatacao";

export type Mes = { inicio: string; fim: string; rotulo: string };

/** Mes (dia 1 ate o dia 1 do mes seguinte) que contem o timestamp de referencia. */
export function mesDe(ts: string): Mes {
  const ano = Number(ts.slice(0, 4));
  const mes = Number(ts.slice(5, 7));
  const dois = (n: number): string => String(n).padStart(2, "0");
  const proxAno = mes === 12 ? ano + 1 : ano;
  const proxMes = mes === 12 ? 1 : mes + 1;
  return {
    inicio: `${ano}-${dois(mes)}-01T00:00:00`,
    fim: `${proxAno}-${dois(proxMes)}-01T00:00:00`,
    rotulo: rotuloMes(ano, mes),
  };
}

/** "de 25/08/2018 a 31/08/2018 (7 dias)" para o periodo que termina em diaRef (AAAA-MM-DD). */
export function rotuloPeriodoDias(diaRef: string, dias: number): string {
  const [a, m, d] = diaRef.split("-").map(Number);
  const ini = new Date(Date.UTC(a ?? 1970, (m ?? 1) - 1, (d ?? 1) - (dias - 1)));
  const br = (x: Date): string =>
    `${String(x.getUTCDate()).padStart(2, "0")}/${String(x.getUTCMonth() + 1).padStart(2, "0")}/${x.getUTCFullYear()}`;
  const fim = new Date(Date.UTC(a ?? 1970, (m ?? 1) - 1, d ?? 1));
  return dias === 1 ? `Dia ${br(fim)}` : `${br(ini)} a ${br(fim)} (${dias} dias)`;
}
