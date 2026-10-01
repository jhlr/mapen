// Unico lugar do dashboard que chama fetch. Quem chega aqui fala so com a API FastAPI.
export const API_URL = process.env.MAPEN_API_URL ?? "http://127.0.0.1:8000";
export const EMPRESA_PADRAO = process.env.MAPEN_EMPRESA_ID ?? "demo";

export type Resposta<T> =
  | { ok: true; status: number; dados: T }
  | { ok: false; status: number; erro: string };

type Opcoes = { corpo?: unknown; aceitar?: readonly number[] };

/** Mensagem legivel a partir do corpo de erro do FastAPI ({detail: string | lista}). */
function detalhe(texto: string): string {
  try {
    const j = JSON.parse(texto) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg ?? ""}`)
        .join("; ");
    }
  } catch {
    /* corpo nao e JSON */
  }
  return texto;
}

/** Chamada tipada; nunca lanca por status HTTP, so por falha de rede (API fora do ar). */
export async function requisitar<T>(
  metodo: "GET" | "POST" | "PATCH",
  caminho: string,
  empresa: string,
  { corpo, aceitar = [] }: Opcoes = {},
): Promise<Resposta<T>> {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: {
      "X-Empresa-Id": empresa,
      ...(corpo === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
    cache: "no-store",
  });
  const texto = await resposta.text();
  if (resposta.ok || aceitar.includes(resposta.status)) {
    return { ok: true, status: resposta.status, dados: JSON.parse(texto) as T };
  }
  return { ok: false, status: resposta.status, erro: detalhe(texto) };
}

/** Leitura para telas: erro vira excecao e cai no error.tsx da rota. */
export async function ler<T>(caminho: string, empresa: string): Promise<T> {
  const r = await requisitar<T>("GET", caminho, empresa);
  if (!r.ok) throw new Error(`API ${r.status} em ${caminho}: ${r.erro}`);
  return r.dados;
}
