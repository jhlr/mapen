import { rotuloMes } from "./formatacao";
import { comFuso, somarDias } from "./fuso";

export type Mes = { inicio: string; fim: string; rotulo: string };

/**
 * Mes (dia 1 ate o dia 1 do mes seguinte) que contem o timestamp de referencia, com offset de Recife.
 * `ts` vem da API com fuso (ts_referencia), entao os 10 primeiros caracteres sao o dia local.
 */
export function mesDe(ts: string): Mes {
  const ano = Number(ts.slice(0, 4));
  const mes = Number(ts.slice(5, 7));
  const dois = (n: number): string => String(n).padStart(2, "0");
  const proxAno = mes === 12 ? ano + 1 : ano;
  const proxMes = mes === 12 ? 1 : mes + 1;
  return {
    inicio: comFuso(`${ano}-${dois(mes)}-01T00:00:00`),
    fim: comFuso(`${proxAno}-${dois(proxMes)}-01T00:00:00`),
    rotulo: rotuloMes(ano, mes),
  };
}

/** "de 25/08/2018 a 31/08/2018 (7 dias)" para o periodo que termina em diaRef (AAAA-MM-DD). */
export function rotuloPeriodoDias(diaRef: string, dias: number): string {
  const br = (x: string): string => `${x.slice(8, 10)}/${x.slice(5, 7)}/${x.slice(0, 4)}`;
  return dias === 1 ? `Dia ${br(diaRef)}` : `${br(somarDias(diaRef, -(dias - 1)))} a ${br(diaRef)} (${dias} dias)`;
}
