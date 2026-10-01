import { custoPorFaixa } from "../api";
import { janelasHorarias, mediaPorHoraDoDia, pontoDaHora, type MediaHora, type PontoHora } from "../dominio/serie";

export type SerieHoraria = { pontos: PontoHora[]; mediaPorHora: MediaHora[]; consultas: number };

const LOTE = 24;

/**
 * A API nao tem endpoint de serie temporal. Monta a serie horaria chamando /custo em janelas de 1 h
 * (kWh em 1 h = kW medio; a faixa tarifaria vem da propria API). O custo e N consultas: 24 por dia.
 */
export async function serieHoraria(
  empresa: string, sensor: string, diaRef: string, dias: number, modalidade: string,
): Promise<SerieHoraria> {
  const janelas = janelasHorarias(diaRef, dias);
  const pontos: PontoHora[] = [];
  for (let i = 0; i < janelas.length; i += LOTE) {
    const lote = janelas.slice(i, i + LOTE);
    const respostas = await Promise.all(
      lote.map((j) => custoPorFaixa(empresa, sensor, j.inicio, j.fim, modalidade)),
    );
    lote.forEach((j, k) => pontos.push(pontoDaHora(j, respostas[k] ?? [])));
  }
  return { pontos, mediaPorHora: mediaPorHoraDoDia(pontos), consultas: janelas.length };
}
