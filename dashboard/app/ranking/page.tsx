import { Barra, Cabecalho, Tabela, Vazio } from "../../components/Basicos";
import { SeletorModalidade, SeletorSensor } from "../../components/Seletores";
import { consumoAgora, ranking } from "../../lib/api";
import { contexto } from "../../lib/contexto";
import { maximoPositivo } from "../../lib/dominio/agregacao";
import { brl, num, pct } from "../../lib/dominio/formatacao";
import { mesDe } from "../../lib/dominio/periodo";
import type { Params } from "../../lib/dominio/parametros";

export const dynamic = "force-dynamic";

export default async function RankingEquipamentos({ searchParams }: { searchParams: Params }) {
  const { empresa, sensores, sensor, modalidade } = await contexto(searchParams);
  if (sensor === undefined) return <Vazio>Nenhum sensor cadastrado para esta empresa.</Vazio>;
  const mes = mesDe((await consumoAgora(empresa, sensor)).ts_referencia);
  const linhas = await ranking(empresa, sensor, mes.inicio, mes.fim, modalidade);
  const maximo = maximoPositivo(linhas.map((l) => l.custo_rs));
  return (
    <>
      <Cabecalho titulo="Ranking de equipamentos por custo" subtitulo={`Referência: ${mes.rotulo}, tarifa ${modalidade}`} />
      <SeletorSensor rota="/ranking" empresa={empresa} sensor={sensor} modalidade={modalidade} sensores={sensores} />
      <SeletorModalidade rota="/ranking" empresa={empresa} sensor={sensor} modalidade={modalidade} />
      {linhas.length === 0 ? <Vazio>Sem consumo no período.</Vazio> : (
        <Tabela legenda="Equipamentos que mais custaram no mês">
          <thead>
            <tr><th>#</th><th>Equipamento</th><th className="n">kWh</th><th className="n">Custo</th><th className="n">Pontos ausentes</th><th className="g" /></tr>
          </thead>
          <tbody>
            {linhas.map((l, i) => (
              <tr key={l.equipamento}>
                <td>{i + 1}</td>
                <td>{l.equipamento}</td>
                <td className="n">{num(l.kwh, 1)}</td>
                <td className="n">{brl(l.custo_rs)}</td>
                <td className="n">{pct(l.pct_ausente)}</td>
                <td className="g"><Barra valor={l.custo_rs} maximo={maximo} /></td>
              </tr>
            ))}
          </tbody>
        </Tabela>
      )}
    </>
  );
}
