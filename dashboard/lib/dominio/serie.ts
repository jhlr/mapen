import type { Custo } from "../api";

export type Janela = { inicio: string; fim: string };
export type PontoHora = { inicio: string; hora: number; kw: number; faixa: string | null };
export type MediaHora = { hora: number; kw: number; faixa: string | null };

const dois = (n: number): string => String(n).padStart(2, "0");
const iso = (d: Date): string =>
  `${d.getUTCFullYear()}-${dois(d.getUTCMonth() + 1)}-${dois(d.getUTCDate())}T${dois(d.getUTCHours())}:00:00`;

/** Janelas de 1 hora cobrindo os `dias` dias que terminam em `diaRef` (AAAA-MM-DD), em ordem. */
export function janelasHorarias(diaRef: string, dias: number): Janela[] {
  const [a, m, d] = diaRef.split("-").map(Number);
  const inicio = Date.UTC(a ?? 1970, (m ?? 1) - 1, (d ?? 1) - (dias - 1));
  return Array.from({ length: dias * 24 }, (_, i) => ({
    inicio: iso(new Date(inicio + i * 3_600_000)),
    fim: iso(new Date(inicio + (i + 1) * 3_600_000)),
  }));
}

/** Soma os equipamentos da janela de 1 h: kWh em 1 h equivale a kW medio. A faixa e a de maior kWh. */
export function pontoDaHora(janela: Janela, linhas: Custo[]): PontoHora {
  const porFaixa = new Map<string, number>();
  let kw = 0;
  for (const l of linhas) {
    kw += l.kwh;
    porFaixa.set(l.faixa, (porFaixa.get(l.faixa) ?? 0) + l.kwh);
  }
  let faixa: string | null = null;
  let melhor = -1;
  for (const [f, v] of porFaixa) if (v > melhor) { faixa = f; melhor = v; }
  return { inicio: janela.inicio, hora: Number(janela.inicio.slice(11, 13)), kw, faixa };
}

/** Media de kW por hora do dia (0..23) sobre todos os dias da serie. */
export function mediaPorHoraDoDia(pontos: PontoHora[]): MediaHora[] {
  return Array.from({ length: 24 }, (_, hora) => {
    const dela = pontos.filter((p) => p.hora === hora);
    const kw = dela.length === 0 ? 0 : dela.reduce((a, p) => a + p.kw, 0) / dela.length;
    const contagem = new Map<string, number>();
    for (const p of dela) if (p.faixa !== null) contagem.set(p.faixa, (contagem.get(p.faixa) ?? 0) + 1);
    const faixa = [...contagem.entries()].sort((x, y) => y[1] - x[1])[0]?.[0] ?? null;
    return { hora, kw, faixa };
  });
}

export type Trecho = { faixa: string | null; de: number; ate: number };

/** Agrupa horas consecutivas da mesma faixa (indices [de, ate) ) para sombrear o fundo do grafico. */
export function trechosDeFaixa(faixas: (string | null)[]): Trecho[] {
  const saida: Trecho[] = [];
  faixas.forEach((f, i) => {
    const ultimo = saida[saida.length - 1];
    if (ultimo !== undefined && ultimo.faixa === f) ultimo.ate = i + 1;
    else saida.push({ faixa: f, de: i, ate: i + 1 });
  });
  return saida;
}
