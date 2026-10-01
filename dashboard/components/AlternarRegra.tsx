"use client";

import { useActionState } from "react";
import { acaoAlterarRegra } from "../actions/cadastro";
import type { Regra } from "../lib/api";

export function AlternarRegra({ empresa, regra }: { empresa: string; regra: Regra }) {
  const [estado, enviar, pendente] = useActionState(acaoAlterarRegra, null);
  return (
    <form action={enviar} className="inline">
      <input type="hidden" name="empresa" value={empresa} />
      <input type="hidden" name="regra_id" value={regra.id} />
      <input type="hidden" name="ativo" value={String(!regra.ativo)} />
      <button type="submit" className="secundario" disabled={pendente}>
        {regra.ativo ? "Desativar" : "Ativar"}
      </button>
      {estado !== null && !estado.ok && <span className="falha" role="alert">{estado.mensagem}</span>}
    </form>
  );
}
