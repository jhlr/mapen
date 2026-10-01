import { Aviso, Cabecalho, Secao, Vazio } from "../../components/Basicos";
import { GraficoMediaPorHora, GraficoSerie, LegendaFaixas } from "../../components/Graficos";
import { SeletorModalidade, SeletorPeriodo, SeletorSensor } from "../../components/Seletores";
import { consumoAgora } from "../../lib/api";
import { contexto } from "../../lib/contexto";
import { rotuloPeriodoDias } from "../../lib/dominio/periodo";
import { diasDe, type Params } from "../../lib/dominio/parametros";
import { serieHoraria } from "../../lib/servicos/serieHoraria";

export const dynamic = "force-dynamic";

export default async function ConsumoPorHora({ searchParams }: { searchParams: Params }) {
  const { empresa, sensores, sensor, modalidade } = await contexto(searchParams);
  if (sensor === undefined) return <Vazio>Nenhum sensor cadastrado para esta empresa.</Vazio>;
  const dias = diasDe((await searchParams).dias);
  const diaRef = (await consumoAgora(empresa, sensor)).ts_referencia.slice(0, 10);
  const serie = await serieHoraria(empresa, sensor, diaRef, dias, modalidade);
  const faixas = serie.pontos.map((p) => p.faixa);
  return (
    <>
      <Cabecalho titulo="Consumo por hora" subtitulo={rotuloPeriodoDias(diaRef, dias)} />
      <SeletorSensor rota="/horario" empresa={empresa} sensor={sensor} modalidade={modalidade} dias={dias} sensores={sensores} />
      <SeletorPeriodo rota="/horario" empresa={empresa} sensor={sensor} modalidade={modalidade} dias={dias} />
      <SeletorModalidade rota="/horario" empresa={empresa} sensor={sensor} modalidade={modalidade} dias={dias} />
      <Aviso titulo="Como ler">
        Soma de todos os equipamentos do sensor. A API não tem endpoint de série temporal: o dashboard consulta o
        custo em janelas de 1 hora ({serie.consultas} consultas), então kWh na hora equivale a kW médio. Horas sem
        leitura entram como 0 kW. O fundo colorido mostra a faixa tarifária ({modalidade}) informada pela API.
      </Aviso>
      <LegendaFaixas faixas={faixas} />
      <Secao titulo="Média por hora do dia">
        <GraficoMediaPorHora medias={serie.mediaPorHora} />
      </Secao>
      <Secao titulo="Potência hora a hora no período">
        <GraficoSerie pontos={serie.pontos} />
      </Secao>
    </>
  );
}
