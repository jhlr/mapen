// View-model das telas do M3 (Modelos, Alertas, Economia): funcoes puras, sem fetch nem React.
import type { Alerta, Economia, MaeEquipamento, MetodoEconomia, Previsao, ResumoModelos } from "../api/tipos";
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
  hora_semana: "hora da semana",
  kw_media24_d24: "média das 24 h (deslocada 24 h)",
  kw_desvio24_d24: "desvio das 24 h (deslocado 24 h)",
  kw_lag48: "kW 48 h antes (lag 48)",
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
const NOMES_METODO: Record<string, string> = {
  baseline_normalizado: "Baseline normalizado",
  diferenca_em_diferencas_grupo_controle: "Grupo-controle (diferença em diferenças)",
};
const NOMES_METODO_CURTOS: Record<string, string> = {
  baseline_normalizado: "Baseline",
  diferenca_em_diferencas_grupo_controle: "Grupo-controle",
};
export const nomeMetodo = (m: MetodoEconomia): string => NOMES_METODO[m.metodo] ?? m.rotulo;
export const nomeMetodoCurto = (metodo: string): string => NOMES_METODO_CURTOS[metodo] ?? metodo;

export type CelulaMetodo = { metodo: string; recuperado: number | null; erro_pp: number | null; fora: boolean; controles: string[]; banda: string };
export type LinhaEconomia = { equipamento: string; alvo: boolean; fraca: boolean; injetado_pct: number; celulas: CelulaMetodo[] };

/** Uma linha por equipamento com o resultado de cada metodo lado a lado (a ordem segue `e.metodos`). */
export function linhasEconomia(e: Economia): LinhaEconomia[] {
  const alvo = e.reducao_sintetica?.equipamento;
  const base = e.metodos[0]?.equipamentos ?? [];
  const porMetodo = e.metodos.map((m) => new Map(m.equipamentos.map((x) => [x.equipamento, x])));
  return base.map((l) => ({
    equipamento: l.equipamento,
    alvo: l.equipamento === alvo,
    fraca: l.baseline_fraca,
    injetado_pct: l.injetado_pct,
    celulas: e.metodos.map((m, i) => {
      const x = porMetodo[i]?.get(l.equipamento) ?? l;
      return {
        metodo: m.metodo,
        recuperado: x.recuperado_pct,
        erro_pp: x.erro_pp,
        fora: !x.dentro_da_tolerancia,
        controles: x.controles,
        banda: `${pct(x.injetado_pct - x.tolerancia_pp)} a ${pct(x.injetado_pct + x.tolerancia_pp)}`,
      };
    }),
  }));
}

export type ResumoMetodo = { metodo: string; nome: string; atendida: boolean; titulo: string; detalhe: string; veredito: MetodoEconomia["veredito"] };

/** Veredito de cada metodo so a partir dos campos da API (a tolerancia e os numeros nunca sao fixos aqui). */
export function resumosMetodos(e: Economia): ResumoMetodo[] {
  return e.metodos.map((m) => {
    const tol = m.equipamentos[0]?.tolerancia_pp;
    const faixa = tol === undefined ? "" : ` (±${num(tol, 1)} pp)`;
    const v = m.veredito;
    return {
      metodo: m.metodo,
      nome: nomeMetodo(m),
      atendida: v.tolerancia_atendida,
      titulo: v.tolerancia_atendida ? `Tolerância${faixa} atendida em dado real` : `Tolerância${faixa} NÃO atendida em dado real`,
      detalhe: v.texto,
      veredito: v,
    };
  });
}

// ---------- Previsao do dia seguinte ----------
const NOMES_PREVISOR: Record<string, string> = {
  seasonal_naive_24: "Naive sazonal 24 h",
  seasonal_naive_168: "Naive sazonal 168 h",
  baseline_sazonal: "Baseline sazonal (média por hora da semana)",
  ridge: "Ridge",
  ets_24_tipo_dia: "ETS (período 24 h por tipo de dia)",
  lightgbm_lag24: "LightGBM (sem lag 1)",
};
export const nomePrevisor = (m: string): string => NOMES_PREVISOR[m] ?? m;

const NOMES_GRUPO: Record<string, string> = { calendario: "Calendário", lags: "Lags (24, 48, 168 h)", janela_movel: "Janela móvel (24 h)" };
export const nomeGrupo = (g: string): string => NOMES_GRUPO[g] ?? g;

export type LinhaMase = { equipamento: string; celulas: { modelo: string; mase: number | null; melhor: boolean; larguraMase: number }[] };

/** MASE por equipamento e previsor; `melhor` marca o menor valor da linha, barras na mesma escala (teto 2). */
export function linhasMase(p: Previsao): LinhaMase[] {
  const teto = 2;
  return p.mase_por_equipamento.map((l) => {
    const valores = p.modelos.map((m) => l.mase[m.modelo] ?? null);
    const menor = Math.min(...valores.filter((v): v is number => v !== null));
    return {
      equipamento: l.equipamento,
      celulas: p.modelos.map((m, i) => {
        const v = valores[i] ?? null;
        return { modelo: m.modelo, mase: v, melhor: v !== null && v === menor, larguraMase: v === null ? 0 : largura(v, teto) };
      }),
    };
  });
}

/** Total de equipamentos em que o previsor teve MASE menor que o da referencia (naive-168). */
export function textoVitorias(m: Previsao["modelos"][number], total: number): string {
  return m.vitorias_vs_naive168 === null ? "referência" : `${num(m.vitorias_vs_naive168, 0)} de ${num(total, 0)}`;
}
