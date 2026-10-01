"use client";

import { useActionState, useEffect, useState } from "react";
import { acaoAlterarConfiguracao } from "../actions/desligamento";
import { Aviso } from "./Basicos";
import { Resultado } from "./Campo";

/**
 * Altera desligamento_remoto_habilitado (PUT /configuracao). Em duas etapas de proposito: o primeiro
 * clique so abre a confirmacao; o PUT sai no segundo e grava o evento configuracao_alterada.
 */
export function ControleRemoto({ habilitado }: { habilitado: boolean }) {
  const [estado, enviar, pendente] = useActionState(acaoAlterarConfiguracao, null);
  const [confirmando, setConfirmando] = useState(false);
  useEffect(() => {
    if (estado !== null) setConfirmando(false);
  }, [estado]);
  const alvo = !habilitado;
  return (
    <section className="secao" aria-labelledby="titulo-remoto">
      <h2 id="titulo-remoto">Desligamento remoto</h2>
      <p className="sub">Estado atual: <b>{habilitado ? "habilitado" : "desabilitado (só recomendação)"}</b></p>
      {!confirmando && (
        <div className="acoes">
          <button type="button" className={alvo ? undefined : "secundario"} onClick={() => setConfirmando(true)}>
            {alvo ? "Habilitar desligamento remoto..." : "Desabilitar desligamento remoto..."}
          </button>
        </div>
      )}
      {confirmando && (
        <form action={enviar} className="form confirma">
          <input type="hidden" name="habilitar" value={String(alvo)} />
          <Aviso tom="atencao" titulo={alvo ? "Confirmar: habilitar desligamento remoto" : "Confirmar: desabilitar desligamento remoto"}>
            {alvo
              ? "Com isso, comandos de desligar assinados e válidos passam a ser aceitos para equipamentos não críticos. Equipamentos críticos continuam protegidos."
              : "Com isso, pedidos de desligar voltam a ser registrados e rejeitados. Religar continua permitido."}{" "}
            A mudança grava o evento configuracao_alterada com o seu usuário e vale para toda a empresa.
          </Aviso>
          <div className="acoes">
            <button type="submit" disabled={pendente}>{pendente ? "Gravando..." : "Confirmar e registrar"}</button>
            <button type="button" className="secundario" disabled={pendente} onClick={() => setConfirmando(false)}>Cancelar</button>
          </div>
        </form>
      )}
      <Resultado estado={estado} />
    </section>
  );
}
