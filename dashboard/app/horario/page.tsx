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
  const { sensores, sensor, modalidade } = await contexto(searchParams);
  if (sensor === undefined) return <Vazio>Nenhum sensor cadastrado para esta empresa.</Vazio>;
  const dias = diasDe((await searchParams).dias);
  const diaRef = (await consumoAgora(sensor)).ts_referencia.slice(0, 10);
  const serie = await serieHoraria(sensor, diaRef, dias, modalidade);
  const faixas = serie.pontos.map((p) => p.faixa);
  return (
    <>
      <Cabecalho titulo="Consumo por hora" subtitulo={rotuloPeriodoDias(diaRef, dias)} />
      <SeletorSensor rota="/horario" sensor={sensor} modalidade={modalidade} dias={dias} sensores={sensores} />
      <SeletorPeriodo rota="/horario" sensor={sensor} modalidade={modalidade} dias={dias} />
      <SeletorModalidade rota="/horario" sensor={sensor} modalidade={modalidade} dias={dias} />
      <Aviso titulo="Como ler">
        Soma de todos os equipamentos do sensor, em kW médio por hora (horário de Recife), vinda de uma única
        chamada a /consumo/horario. O fundo colorido é a faixa tarifária ({modalidade}) informada pela API; a
        faixa ponta tem hachura. {serie.horasAusentes === 0
          ? "Todas as horas do período têm leitura."
          : `${serie.horasAusentes} hora(s) do período sem leitura: aparecem como 0 kW no gráfico hora a hora e ficam fora da média por hora do dia.`}
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
