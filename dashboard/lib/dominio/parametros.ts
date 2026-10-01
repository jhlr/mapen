export type Params = Promise<Record<string, string | string[] | undefined>>;

export function primeiro(valor: string | string[] | undefined): string | undefined {
  return Array.isArray(valor) ? valor[0] : valor;
}

export const MODALIDADES = ["branca", "convencional"] as const;
export type Modalidade = (typeof MODALIDADES)[number];
export const ehModalidade = (v: string | undefined): v is Modalidade => MODALIDADES.some((m) => m === v);

/** Querystring que preserva empresa (e, se houver, sensor/modalidade). */
export function consulta(partes: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(partes)) if (v !== undefined) q.set(k, String(v));
  const s = q.toString();
  return s === "" ? "" : `?${s}`;
}

export const PERIODOS_DIAS = [1, 3, 7] as const;
/** Limite de 7 dias: a serie horaria custa 24 consultas por dia. */
export function diasDe(valor: string | string[] | undefined): number {
  const n = Number(primeiro(valor));
  return PERIODOS_DIAS.find((d) => d === n) ?? 7;
}
