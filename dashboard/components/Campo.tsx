import type { ReactNode } from "react";

export function Campo({ rotulo, dica, children }: { rotulo: string; dica?: string; children: ReactNode }) {
  return (
    <label className="campo">
      <span className="campo-rotulo">{rotulo}</span>
      {children}
      {dica !== undefined && <span className="dica">{dica}</span>}
    </label>
  );
}

export function Resultado({ estado }: { estado: { ok: boolean; mensagem: string } | null }) {
  if (estado === null) return null;
  return (
    <p className={estado.ok ? "resultado ok" : "resultado falha"} role={estado.ok ? "status" : "alert"}>
      {estado.mensagem}
    </p>
  );
}
