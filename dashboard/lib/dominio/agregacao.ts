import type { Custo } from "../api";

export type LinhaFaixa = { faixa: string; kwh: number; rs: number };

export function agruparPorFaixa(linhas: Custo[]): LinhaFaixa[] {
  const mapa = new Map<string, LinhaFaixa>();
  for (const l of linhas) {
    const a = mapa.get(l.faixa) ?? { faixa: l.faixa, kwh: 0, rs: 0 };
    mapa.set(l.faixa, { faixa: l.faixa, kwh: a.kwh + l.kwh, rs: a.rs + l.custo_rs });
  }
  return [...mapa.values()];
}

export const somaRs = (linhas: LinhaFaixa[]): number => linhas.reduce((a, l) => a + l.rs, 0);
export const maximoPositivo = (valores: number[]): number => Math.max(...valores, 1e-9);
