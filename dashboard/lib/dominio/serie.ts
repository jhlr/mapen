import type { PontoHorario } from "../api";
import { somarDias } from "./fuso";

export type PontoHora = { inicio: string; hora: number; kw: number; faixa: string | null; ausente: boolean };
export type MediaHora = { hora: number; kw: number; faixa: string | null };

const dois = (n: number): string => String(n).padStart(2, "0");

/** Faixa mais frequente por hora do dia entre os pontos devolvidos pela API (nao duplica a regra tarifaria). */
function faixaTipica(pontos: PontoHorario[]): Map<number, string> {
  const contagem = new Map<number, Map<string, number>>();
  for (const p of pontos) {
    const h = Number(p.hora.slice(11, 13));
    const c = contagem.get(h) ?? new Map<string, number>();
    c.set(p.faixa, (c.get(p.faixa) ?? 0) + 1);
    contagem.set(h, c);
  }
  const saida = new Map<number, string>();
  for (const [h, c] of contagem) {
    const melhor = [...c.entries()].sort((x, y) => y[1] - x[1])[0];
    if (melhor !== undefined) saida.set(h, melhor[0]);
  }
  return saida;
}

/**
 * Grade de 24 x `dias` horas locais terminando em `diaRef` (AAAA-MM-DD), preenchida com os pontos da API
 * (`hora` tem offset de Recife, entao os caracteres 0..13 sao a hora local). Hora sem leitura: 0 kW,
 * marcada `ausente`, com a faixa tipica daquela hora do dia (so para sombrear o fundo).
 */
export function montarGrade(diaRef: string, dias: number, pontos: PontoHorario[]): PontoHora[] {
  const porHora = new Map(pontos.map((p) => [p.hora.slice(0, 13), p]));
  const tipica = faixaTipica(pontos);
  const grade: PontoHora[] = [];
  for (let d = dias - 1; d >= 0; d--) {
    const dia = somarDias(diaRef, -d);
    for (let h = 0; h < 24; h++) {
      const p = porHora.get(`${dia}T${dois(h)}`);
      grade.push({
        inicio: `${dia}T${dois(h)}:00:00`,
        hora: h,
        kw: p?.kw ?? 0,
        faixa: p?.faixa ?? tipica.get(h) ?? null,
        ausente: p === undefined,
      });
    }
  }
  return grade;
}

/** Media de kW por hora do dia (0..23) sobre as horas COM leitura. */
export function mediaPorHoraDoDia(pontos: PontoHora[]): MediaHora[] {
  return Array.from({ length: 24 }, (_, hora) => {
    const dela = pontos.filter((p) => p.hora === hora && !p.ausente);
    const kw = dela.length === 0 ? 0 : dela.reduce((a, p) => a + p.kw, 0) / dela.length;
    const contagem = new Map<string, number>();
    for (const p of pontos) if (p.hora === hora && p.faixa !== null) contagem.set(p.faixa, (contagem.get(p.faixa) ?? 0) + 1);
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
