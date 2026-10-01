// Unico ponto de acesso do dashboard: ele so conversa com a API FastAPI.
const API = process.env.MAPEN_API_URL ?? "http://127.0.0.1:8000";
export const EMPRESA_PADRAO = process.env.MAPEN_EMPRESA_ID ?? "demo";

export type Sensor = { id: string; unidade_id: string; nome: string };
export type Equipamento = { id: string; sensor_id: string; nome: string; critico: boolean };
export type Regra = {
  id: string;
  equipamento_id: string;
  cron: string;
  ativo: boolean;
  autorizado_por: string;
  criado_em: string;
};
export type ConsumoAgora = {
  sensor_id: string;
  ts_referencia: string;
  potencia_w: number;
  kwh_dia: number;
  por_equipamento: { equipamento: string; kwh: number }[];
};
export type Custo = { equipamento: string; faixa: string; kwh: number; custo_rs: number };
export type Ranking = { equipamento: string; kwh: number; custo_rs: number; pct_ausente: number };
export type Evento = {
  id: string;
  ts: string;
  tipo: string;
  sensor_id: string | null;
  equipamento_id: string | null;
  origem: string;
  regra_id: string | null;
  autorizado_por: string | null;
  payload: Record<string, string>;
};

export async function buscar<T>(caminho: string, empresa: string): Promise<T> {
  const resposta = await fetch(`${API}${caminho}`, {
    headers: { "X-Empresa-Id": empresa },
    cache: "no-store",
  });
  if (!resposta.ok) {
    throw new Error(`API ${resposta.status} em ${caminho}: ${await resposta.text()}`);
  }
  return (await resposta.json()) as T;
}

export type Busca = { sensor?: string; empresa?: string; modalidade?: string };

export function primeiro(valor: string | string[] | undefined): string | undefined {
  return Array.isArray(valor) ? valor[0] : valor;
}

/** Mes (AAAA-MM-01 ate o mes seguinte) que contem o timestamp de referencia. */
export function mesDe(ts: string): { inicio: string; fim: string; rotulo: string } {
  const ano = Number(ts.slice(0, 4));
  const mes = Number(ts.slice(5, 7));
  const dois = (n: number): string => String(n).padStart(2, "0");
  const proxAno = mes === 12 ? ano + 1 : ano;
  const proxMes = mes === 12 ? 1 : mes + 1;
  return {
    inicio: `${ano}-${dois(mes)}-01T00:00:00`,
    fim: `${proxAno}-${dois(proxMes)}-01T00:00:00`,
    rotulo: `${ano}-${dois(mes)}`,
  };
}

export const brl = (v: number): string =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export const num = (v: number, casas = 1): string =>
  v.toLocaleString("pt-BR", { maximumFractionDigits: casas });
