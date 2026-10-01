import { Aviso, Barra, Cabecalho, Cartao, Cartoes, Tabela, Vazio } from "../../components/Basicos";
import { SeletorModalidade, SeletorSensor } from "../../components/Seletores";
import { consumoAgora, custoPorFaixa } from "../../lib/api";
import { contexto } from "../../lib/contexto";
import { agruparPorFaixa, maximoPositivo, somaRs } from "../../lib/dominio/agregacao";
import { brl, num } from "../../lib/dominio/formatacao";
import { mesDe } from "../../lib/dominio/periodo";
import type { Params } from "../../lib/dominio/parametros";

export const dynamic = "force-dynamic";

export default async function CustoPorFaixa({ searchParams }: { searchParams: Params }) {
  const { empresa, sensores, sensor, modalidade } = await contexto(searchParams);
  if (sensor === undefined) return <Vazio>Nenhum sensor cadastrado para esta empresa.</Vazio>;
  const mes = mesDe((await consumoAgora(empresa, sensor)).ts_referencia);
  const faixas = agruparPorFaixa(await custoPorFaixa(empresa, sensor, mes.inicio, mes.fim, modalidade));
  const maximo = maximoPositivo(faixas.map((f) => f.rs));
  return (
    <>
      <Cabecalho titulo="Custo por faixa horária" subtitulo={`Referência: ${mes.rotulo}`} />
      <SeletorSensor rota="/custo" empresa={empresa} sensor={sensor} modalidade={modalidade} sensores={sensores} />
      <SeletorModalidade rota="/custo" empresa={empresa} sensor={sensor} modalidade={modalidade} />
      <Aviso titulo="Como ler">
        Tarifa base Neoenergia PE B3, sem tributos e sem bandeira. Pontos ausentes não entram na soma, então o
        custo é um piso.
      </Aviso>
      <Cartoes><Cartao rotulo={`Total no mês (${modalidade})`} valor={brl(somaRs(faixas))} /></Cartoes>
      {faixas.length === 0 ? <Vazio>Sem consumo no período.</Vazio> : (
        <Tabela legenda="Custo por faixa horária">
          <thead><tr><th>Faixa</th><th className="n">kWh</th><th className="n">Custo</th><th className="g" /></tr></thead>
          <tbody>
            {faixas.map((f) => (
              <tr key={f.faixa}>
                <td>{f.faixa}</td>
                <td className="n">{num(f.kwh, 1)}</td>
                <td className="n">{brl(f.rs)}</td>
                <td className="g"><Barra valor={f.rs} maximo={maximo} /></td>
              </tr>
            ))}
          </tbody>
        </Tabela>
      )}
    </>
  );
}
