// View-model das telas do M3 (Modelos, Alertas, Economia): funcoes puras, sem fetch nem React.
import type { Alerta, Economia, EconomiaEquipamento, MaeEquipamento, ResumoModelos } from "../api/tipos";
import { num, pct } from "./formatacao";
import { primeiro } from "./parametros";

const NOMES_TIPO: Record<string, string> = {
  zscore: "z-score",
  lightgbm: "LightGBM",
  pico: "pico",
  elevacao_fora_de_horario: "elevação fora de horário",
  ligado_continuo: "ligado contínuo",
};
export const nomeTipo = (t: string): string => NOMES_TIPO[t] ?? t;
export const TIPOS_ALERTA = ["zscore", "lightgbm"] as const;

const NOMES_FEATURE: Record<string, string> = {
  hora: "hora do dia",
  dia_semana: "dia da semana",
  feriado: "feriado",
  kw_lag1: "kW 1 h antes (lag 1)",
  kw_lag24: "kW 24 h antes (lag 24)",
  kw_lag168: "kW 168 h antes (lag 168)",
  kw_media24: "média das 24 h",
  kw_desvio24: "desvio das 24 h",
};
export const nomeFeature = (f: string): string => NOMES_FEATURE[f] ?? f;

/** Largura relativa (0..100) de um valor frente ao maximo. */
export const largura = (v: number, maximo: number): number => (maximo > 0 ? Math.max(0, Math.min(100, (100 * v) / maximo)) : 0);

export const kw = (v: number, casas = 2): string => `${num(v, casas)} kW`;
export const pp = (v: number): string => `${v > 0 ? "+" : ""}${num(v, 1)} pp`;

/** "2018-07-01T00:00:00-03:00" -> "01/07/2018" (a API ja devolve o fuso de Recife). */
export function dia(ts: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ts);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : ts;
}

// ---------- Modelos ----------
export type LinhaMae = MaeEquipamento & { larguraBaseline: number; larguraLightgbm: number; fraca: boolean };

export function linhasMae(resumo: ResumoModelos): { linhas: LinhaMae[]; maximo: number } {
  const lista = resumo.mae?.por_equipamento ?? [];
  const fracas = new Set(resumo.baseline_fraca?.equipamentos ?? []);
  const maximo = Math.max(0, ...lista.flatMap((l) => [l.mae_baseline_kw, l.mae_lightgbm_kw]));
  const linhas = lista.map((l) => ({
    ...l,
    larguraBaseline: largura(l.mae_baseline_kw, maximo),
    larguraLightgbm: largura(l.mae_lightgbm_kw, maximo),
    fraca: fracas.has(l.equipamento),
  }));
  return { linhas, maximo };
}

/** Frase do aviso D7, montada so com os campos da API; `null` quando nao disparou. */
export function textoAvisoD7(aviso: NonNullable<ResumoModelos["shap"]>["aviso_d7"]): string | null {
  if (aviso === null || !aviso.disparado || aviso.feature === null || aviso.pct === null) return null;
  return `A feature ${nomeFeature(aviso.feature)} responde por ${pct(aviso.pct)} da importância SHAP, acima do limiar de ${pct(aviso.limiar_pct)}; ${aviso.equipamentos_com_dominante} equipamento(s) têm uma feature dominante. O modelo depende sobretudo do consumo da hora anterior.`;
}

export function resumoPeriodo(i: { inicio: string; fim: string }): string {
  return `${dia(i.inicio)} a ${dia(i.fim)}`;
}

// ---------- Alertas ----------
export type FiltrosAlertasUrl = { equipamento?: string; tipo?: string; de?: string; ate?: string; pagina: number; erro?: string };
export const ALERTAS_POR_PAGINA = 25;
const DATA = /^\d{4}-\d{2}-\d{2}$/;
const dataValida = (v: string | undefined): v is string => v !== undefined && DATA.test(v) && !Number.isNaN(Date.parse(`${v}T00:00:00Z`));

/** Le os filtros da URL; valor invalido some (nunca vira parametro da API). */
export function lerFiltrosAlertas(p: Record<string, string | string[] | undefined>, equipamentos: readonly string[]): FiltrosAlertasUrl {
  const eq = primeiro(p.equipamento);
  const tipo = primeiro(p.tipo);
  const de = primeiro(p.de);
  const ate = primeiro(p.ate);
  const pagina = Number(primeiro(p.pagina));
  const f: FiltrosAlertasUrl = {
    equipamento: eq !== undefined && equipamentos.includes(eq) ? eq : undefined,
    tipo: TIPOS_ALERTA.find((t) => t === tipo),
    de: dataValida(de) ? de : undefined,
    ate: dataValida(ate) ? ate : undefined,
    pagina: Number.isInteger(pagina) && pagina >= 1 ? pagina : 1,
  };
  if (f.de !== undefined && f.ate !== undefined && f.de > f.ate) return { ...f, de: undefined, ate: undefined, erro: "A data inicial é posterior à final; o filtro de período foi ignorado." };
  return f;
}

const FUSO = "-03:00";
const maisUmDia = (d: string): string => new Date(Date.parse(`${d}T00:00:00Z`) + 86_400_000).toISOString().slice(0, 10);

/** Filtros da URL (dias locais, `ate` inclusivo) -> parametros da API (`de` inclusivo, `ate` exclusivo, com fuso). */
export function paraApi(f: FiltrosAlertasUrl): { equipamento?: string; tipo?: string; de?: string; ate?: string; limite: number; offset: number } {
  return {
    equipamento: f.equipamento,
    tipo: f.tipo,
    de: f.de === undefined ? undefined : `${f.de}T00:00:00${FUSO}`,
    ate: f.ate === undefined ? undefined : `${maisUmDia(f.ate)}T00:00:00${FUSO}`,
    limite: ALERTAS_POR_PAGINA,
    offset: (f.pagina - 1) * ALERTAS_POR_PAGINA,
  };
}

export function hrefAlertas(f: FiltrosAlertasUrl, pagina: number): string {
  const q = new URLSearchParams();
  if (f.equipamento !== undefined) q.set("equipamento", f.equipamento);
  if (f.tipo !== undefined) q.set("tipo", f.tipo);
  if (f.de !== undefined) q.set("de", f.de);
  if (f.ate !== undefined) q.set("ate", f.ate);
  if (pagina > 1) q.set("pagina", String(pagina));
  const s = q.toString();
  return s === "" ? "/alertas" : `/alertas?${s}`;
}

export type LinhaAlerta = {
  chave: string;
  alerta: Alerta;
  larguraEsperado: number;
  larguraObservado: number;
  desvio: string;
};

/** Esperado e observado na mesma escala por alerta; desvio em % do esperado (sinal indica o sentido). */
export function linhasAlertas(itens: Alerta[]): LinhaAlerta[] {
  return itens.map((a) => {
    const { esperado_kw: e, observado_kw: o } = a.explicacao;
    const maximo = Math.max(e, o);
    return {
      chave: `${a.timestamp}|${a.equipamento}|${a.tipo}`,
      alerta: a,
      larguraEsperado: largura(e, maximo),
      larguraObservado: largura(o, maximo),
      desvio: e > 0 ? `${o >= e ? "+" : "−"}${num(Math.abs(100 * (o - e) / e), 0)}% do esperado` : "esperado ≈ 0",
    };
  });
}

export function faixaDeItens(total: number, offset: number, qtd: number): string {
  if (total === 0 || qtd === 0) return "0 alertas";
  return `${num(offset + 1, 0)} a ${num(offset + qtd, 0)} de ${num(total, 0)} alertas`;
}

// ---------- Economia ----------
export type LinhaEconomia = EconomiaEquipamento & { alvo: boolean; fora: boolean; banda: string; larguraInjetado: number; larguraRecuperado: number };

export function linhasEconomia(e: Economia): LinhaEconomia[] {
  const alvo = e.reducao_sintetica?.equipamento;
  const maximo = Math.max(0, ...e.equipamentos.flatMap((l) => [l.injetado_pct, l.recuperado_pct ?? 0]));
  return e.equipamentos.map((l) => ({
    ...l,
    alvo: l.equipamento === alvo,
    fora: !l.dentro_da_tolerancia,
    banda: `${pct(l.injetado_pct - l.tolerancia_pp)} a ${pct(l.injetado_pct + l.tolerancia_pp)}`,
    larguraInjetado: largura(l.injetado_pct, maximo),
    larguraRecuperado: largura(l.recuperado_pct ?? 0, maximo),
  }));
}

export type VereditoEconomia = { atendida: boolean; titulo: string; detalhe: string };

/** Veredito so a partir dos campos da API (a tolerancia e os numeros nunca sao fixos aqui). */
export function vereditoEconomia(e: Economia): VereditoEconomia | null {
  const v = e.veredito;
  if (v === null) return null;
  const tol = e.equipamentos[0]?.tolerancia_pp;
  const faixa = tol === undefined ? "" : ` (±${num(tol, 1)} pp)`;
  return {
    atendida: v.tolerancia_atendida,
    titulo: v.tolerancia_atendida ? `Tolerância${faixa} atendida em dado real` : `Tolerância${faixa} NÃO atendida em dado real`,
    detalhe: v.texto,
  };
}
