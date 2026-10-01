import { Aviso, Barra, Cabecalho, Cartao, Cartoes, Tabela, Vazio } from "../components/Basicos";
import { SeletorSensor } from "../components/Seletores";
import { consumoAgora } from "../lib/api";
import { contexto } from "../lib/contexto";
import { dataHora, kwh, num, watts } from "../lib/dominio/formatacao";
import { maximoPositivo } from "../lib/dominio/agregacao";
import type { Params } from "../lib/dominio/parametros";

export const dynamic = "force-dynamic";

export default async function Consumo({ searchParams }: { searchParams: Params }) {
  const { empresa, sensores, sensor } = await contexto(searchParams);
  if (sensor === undefined) return <Vazio>Nenhum sensor cadastrado para esta empresa.</Vazio>;
  const c = await consumoAgora(empresa, sensor);
  const maximo = maximoPositivo(c.por_equipamento.map((x) => x.kwh));
  return (
    <>
      <Cabecalho titulo="Consumo agora e hoje" subtitulo={`Última leitura: ${dataHora(c.ts_referencia)}`} />
      <SeletorSensor rota="/" empresa={empresa} sensor={sensor} sensores={sensores} />
      <Aviso titulo="Dado de demonstração (histórico)">
        &quot;Agora&quot; é a última leitura do sensor e &quot;hoje&quot; é o dia dessa leitura.
      </Aviso>
      <Cartoes>
        <Cartao rotulo="Potência agora" valor={watts(c.potencia_w)} />
        <Cartao rotulo="Consumo no dia" valor={kwh(c.kwh_dia)} />
      </Cartoes>
      <Tabela legenda="Consumo no dia por equipamento">
        <thead><tr><th>Equipamento</th><th className="n">kWh no dia</th><th className="g" /></tr></thead>
        <tbody>
          {c.por_equipamento.map((x) => (
            <tr key={x.equipamento}>
              <td>{x.equipamento}</td>
              <td className="n">{num(x.kwh, 2)}</td>
              <td className="g"><Barra valor={x.kwh} maximo={maximo} /></td>
            </tr>
          ))}
        </tbody>
      </Tabela>
    </>
  );
}
