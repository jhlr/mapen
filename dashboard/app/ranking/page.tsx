import { brl, buscar, mesDe, num, type ConsumoAgora, type Ranking } from "../../lib/api";
import { contexto, type Params } from "../../lib/contexto";

export const dynamic = "force-dynamic";

export default async function RankingEquipamentos({ searchParams }: { searchParams: Params }) {
  const { empresa, sensor, modalidade } = await contexto(searchParams);
  if (sensor === undefined) return <p>Nenhum sensor cadastrado.</p>;
  const id = encodeURIComponent(sensor);
  const ref = await buscar<ConsumoAgora>(`/sensores/${id}/consumo-agora`, empresa);
  const mes = mesDe(ref.ts_referencia);
  const linhas = await buscar<Ranking[]>(
    `/sensores/${id}/ranking?inicio=${mes.inicio}&fim=${mes.fim}&modalidade=${modalidade}&n=10`,
    empresa,
  );
  const maximo = Math.max(...linhas.map((l) => l.custo_rs), 1e-9);
  return (
    <>
      <h1>Ranking de equipamentos por custo, {mes.rotulo}</h1>
      <table>
        <thead>
          <tr><th>#</th><th>Equipamento</th><th className="n">kWh</th><th className="n">Custo</th><th className="n">% ausente</th><th /></tr>
        </thead>
        <tbody>
          {linhas.map((l, i) => (
            <tr key={l.equipamento}>
              <td>{i + 1}</td>
              <td>{l.equipamento}</td>
              <td className="n">{num(l.kwh, 1)}</td>
              <td className="n">{brl(l.custo_rs)}</td>
              <td className="n">{num(l.pct_ausente, 1)}</td>
              <td style={{ width: "30%" }}><div className="barra" style={{ width: `${(100 * l.custo_rs) / maximo}%` }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
