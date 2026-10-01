"use client";

import { useActionState } from "react";
import { acaoCriarRegra } from "../actions/cadastro";
import type { Equipamento } from "../lib/api";
import { Campo, Resultado } from "./Campo";

export function FormRegra({ empresa, equipamentos }: { empresa: string; equipamentos: Equipamento[] }) {
  const [estado, enviar, pendente] = useActionState(acaoCriarRegra, null);
  return (
    <form action={enviar} className="form">
      <input type="hidden" name="empresa" value={empresa} />
      <Campo rotulo="Equipamento">
        <select name="equipamento_id" required defaultValue={estado?.valores.equipamento_id}>
          {equipamentos.map((e) => (
            <option key={e.id} value={e.id}>{e.nome}{e.critico ? " (crítico)" : ""}</option>
          ))}
        </select>
      </Campo>
      <Campo rotulo="Agenda (cron)" dica="Cinco campos: minuto hora dia mês dia-da-semana. Ex.: 0 22 * * 1-5 = 22h, de segunda a sexta.">
        <input name="cron" required defaultValue={estado?.valores.cron} placeholder="0 22 * * 1-5" pattern="\S+( \S+){4}" title="cinco campos separados por espaço" />
      </Campo>
      <Campo rotulo="Autorizado por" dica="Obrigatório: pessoa responsável por essa regra. Fica registrada em cada evento.">
        <input name="autorizado_por" required defaultValue={estado?.valores.autorizado_por} placeholder="nome ou e-mail" />
      </Campo>
      <label className="check">
        <input type="checkbox" name="ativo" defaultChecked={estado === null || estado.ok || estado.valores.ativo === "on"} />
        <span><b>Criar ativa</b></span>
      </label>
      <p className="dica">
        A regra é só cadastrada: nenhum agendador a executa ainda, e o desligamento remoto segue a configuração da API.
      </p>
      <div className="acoes">
        <button type="submit" disabled={pendente || equipamentos.length === 0}>{pendente ? "Criando..." : "Criar regra"}</button>
      </div>
      <Resultado estado={estado} />
    </form>
  );
}
