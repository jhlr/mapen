"use client";

import { useActionState } from "react";
import { acaoCriarEquipamento } from "../actions/cadastro";
import type { Sensor } from "../lib/api";
import { Campo, Resultado } from "./Campo";

export function FormEquipamento({ empresa, sensores }: { empresa: string; sensores: Sensor[] }) {
  const [estado, enviar, pendente] = useActionState(acaoCriarEquipamento, null);
  return (
    <form action={enviar} className="form">
      <input type="hidden" name="empresa" value={empresa} />
      <Campo rotulo="Sensor">
        <select name="sensor_id" required defaultValue={estado?.valores.sensor_id}>
          {sensores.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
        </select>
      </Campo>
      <Campo rotulo="Nome do equipamento">
        <input name="nome" required maxLength={80} defaultValue={estado?.valores.nome} placeholder="ex.: z3_AC1" />
      </Campo>
      <label className="check">
        <input type="checkbox" name="critico" defaultChecked={estado?.valores.critico === "on"} />
        <span>
          <b>Equipamento crítico</b>
          <span className="dica">
            Marque se a parada causa dano (refrigeração de vacinas, ar de CTI, servidor). A API recusa qualquer
            comando de desligamento remoto para um equipamento crítico, mesmo com regra e autorização.
          </span>
        </span>
      </label>
      <div className="acoes">
        <button type="submit" disabled={pendente || sensores.length === 0}>{pendente ? "Criando..." : "Criar equipamento"}</button>
      </div>
      <Resultado estado={estado} />
    </form>
  );
}
