import "server-only";
import { unauthorized } from "next/navigation";

// Unico lugar do dashboard que chama fetch. Roda so no servidor (server-only quebra o build se um
// componente de cliente importar este modulo). A chave de API vem de variavel de ambiente SEM o
// prefixo NEXT_PUBLIC_, entao nunca vai para o JavaScript do navegador.
export const API_URL = process.env.MAPEN_API_URL ?? "http://127.0.0.1:8000";

export type Resposta<T> =
  | { ok: true; status: number; dados: T }
  | { ok: false; status: number; erro: string };

type Opcoes = { corpo?: unknown; aceitar?: readonly number[] };

const SEM_CHAVE = "MAPEN_API_KEY não está definida no servidor do dashboard.";

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
  metodo: "GET" | "POST" | "PATCH" | "PUT",
  caminho: string,
  { corpo, aceitar = [] }: Opcoes = {},
): Promise<Resposta<T>> {
  const chave = process.env.MAPEN_API_KEY?.trim();
  if (chave === undefined || chave === "") return { ok: false, status: 401, erro: SEM_CHAVE };
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: {
      Authorization: `Bearer ${chave}`,
      ...(corpo === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
    cache: "no-store",
  });
  const texto = await resposta.text();
  if (resposta.ok || aceitar.includes(resposta.status)) {
    return { ok: true, status: resposta.status, dados: JSON.parse(texto) as T };
  }
  return { ok: false, status: resposta.status, erro: resposta.status === 401 ? "chave de API recusada" : detalhe(texto) };
}

/**
 * Leitura para telas. 401 (chave ausente ou recusada) renderiza app/unauthorized.tsx com status 401;
 * os demais erros viram excecao e caem no error.tsx da rota.
 */
export async function ler<T>(caminho: string): Promise<T> {
  const r = await requisitar<T>("GET", caminho);
  if (!r.ok) {
    if (r.status === 401) unauthorized();
    throw new Error(`API ${r.status} em ${caminho}: ${r.erro}`);
  }
  return r.dados;
}
