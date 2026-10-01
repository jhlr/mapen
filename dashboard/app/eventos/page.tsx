import { buscar, EMPRESA_PADRAO, primeiro, type Evento } from "../../lib/api";
import type { Params } from "../../lib/contexto";

export const dynamic = "force-dynamic";

export default async function Eventos({ searchParams }: { searchParams: Params }) {
  const empresa = primeiro((await searchParams).empresa) ?? EMPRESA_PADRAO;
  const eventos = await buscar<Evento[]>("/eventos?limite=100", empresa);
  return (
    <>
      <h1>Alertas e eventos</h1>
      {eventos.length === 0 && <p>Nenhum evento registrado.</p>}
      <table>
        <thead><tr><th>Quando (UTC)</th><th>Tipo</th><th>Equipamento</th><th>Origem</th><th>Regra</th><th>Autorizado por</th><th>Detalhe</th></tr></thead>
        <tbody>
          {eventos.map((e) => (
            <tr key={e.id}>
              <td>{e.ts}</td>
              <td className={e.tipo === "comando_rejeitado" ? "rej" : undefined}>{e.tipo}</td>
              <td>{e.equipamento_id ?? "-"}</td>
              <td>{e.origem}</td>
              <td>{e.regra_id ?? "-"}</td>
              <td>{e.autorizado_por ?? "-"}</td>
              <td>{JSON.stringify(e.payload)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
