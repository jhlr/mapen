import { buscar, num, type ConsumoAgora } from "../lib/api";
import { contexto, type Params } from "../lib/contexto";

export const dynamic = "force-dynamic";

export default async function Consumo({ searchParams }: { searchParams: Params }) {
  const { empresa, sensores, sensor } = await contexto(searchParams);
  if (sensor === undefined) return <p>Nenhum sensor cadastrado.</p>;
  const c = await buscar<ConsumoAgora>(`/sensores/${encodeURIComponent(sensor)}/consumo-agora`, empresa);
  const maximo = Math.max(...c.por_equipamento.map((x) => x.kwh), 1e-9);
  return (
    <>
      <h1>Consumo agora e hoje</h1>
      <p>
        Sensores:{" "}
        {sensores.map((s) => (
          <a key={s.id} href={`/?empresa=${empresa}&sensor=${encodeURIComponent(s.id)}`}>
            {s.nome}{" "}
          </a>
        ))}
      </p>
      <div className="aviso">
        Dado de demonstracao (historico): &quot;agora&quot; e a ultima leitura do sensor ({c.ts_referencia}) e
        &quot;hoje&quot; e o dia dessa leitura.
      </div>
      <div className="cards">
        <div className="card">Potencia agora<b>{num(c.potencia_w, 0)} W</b></div>
        <div className="card">Consumo no dia<b>{num(c.kwh_dia, 1)} kWh</b></div>
      </div>
      <table>
        <thead><tr><th>Equipamento</th><th className="n">kWh no dia</th><th /></tr></thead>
        <tbody>
          {c.por_equipamento.map((x) => (
            <tr key={x.equipamento}>
              <td>{x.equipamento}</td>
              <td className="n">{num(x.kwh, 2)}</td>
              <td style={{ width: "40%" }}><div className="barra" style={{ width: `${(100 * x.kwh) / maximo}%` }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
