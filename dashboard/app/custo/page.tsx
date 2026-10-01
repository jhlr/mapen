import { brl, buscar, mesDe, num, type ConsumoAgora, type Custo } from "../../lib/api";
import { contexto, type Params } from "../../lib/contexto";

export const dynamic = "force-dynamic";

export default async function CustoPorFaixa({ searchParams }: { searchParams: Params }) {
  const { empresa, sensor, modalidade } = await contexto(searchParams);
  if (sensor === undefined) return <p>Nenhum sensor cadastrado.</p>;
  const id = encodeURIComponent(sensor);
  const ref = await buscar<ConsumoAgora>(`/sensores/${id}/consumo-agora`, empresa);
  const mes = mesDe(ref.ts_referencia);
  const linhas = await buscar<Custo[]>(
    `/sensores/${id}/custo?inicio=${mes.inicio}&fim=${mes.fim}&modalidade=${modalidade}`,
    empresa,
  );
  const porFaixa = new Map<string, { kwh: number; rs: number }>();
  for (const l of linhas) {
    const atual = porFaixa.get(l.faixa) ?? { kwh: 0, rs: 0 };
    porFaixa.set(l.faixa, { kwh: atual.kwh + l.kwh, rs: atual.rs + l.custo_rs });
  }
  const total = [...porFaixa.values()].reduce((a, b) => a + b.rs, 0);
  const maximo = Math.max(...[...porFaixa.values()].map((v) => v.rs), 1e-9);
  return (
    <>
      <h1>Custo por faixa horaria, {mes.rotulo}</h1>
      <p>
        Modalidade: <a href={`/custo?empresa=${empresa}&sensor=${id}&modalidade=convencional`}>convencional</a>{" "}
        | <a href={`/custo?empresa=${empresa}&sensor=${id}&modalidade=branca`}>branca</a> (atual: {modalidade})
      </p>
      <div className="aviso">
        Tarifa base Neoenergia PE B3, sem tributos e sem bandeira. Pontos ausentes nao entram na soma, entao o
        custo e um piso.
      </div>
      <div className="cards"><div className="card">Total no mes<b>{brl(total)}</b></div></div>
      <table>
        <thead><tr><th>Faixa</th><th className="n">kWh</th><th className="n">Custo</th><th /></tr></thead>
        <tbody>
          {[...porFaixa.entries()].map(([faixa, v]) => (
            <tr key={faixa}>
              <td>{faixa}</td>
              <td className="n">{num(v.kwh, 1)}</td>
              <td className="n">{brl(v.rs)}</td>
              <td style={{ width: "35%" }}><div className="barra" style={{ width: `${(100 * v.rs) / maximo}%` }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
