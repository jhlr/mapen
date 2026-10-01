import { consumoHorario } from "../api";
import { intervaloDeDias, somarDias } from "../dominio/fuso";
import { mediaPorHoraDoDia, montarGrade, type MediaHora, type PontoHora } from "../dominio/serie";

export type SerieHoraria = { pontos: PontoHora[]; mediaPorHora: MediaHora[]; horasAusentes: number };

/** Uma chamada a GET /consumo/horario (kW por hora e faixa tarifaria, calculados pela API). */
export async function serieHoraria(sensor: string, diaRef: string, dias: number, modalidade: string): Promise<SerieHoraria> {
  const { inicio, fim } = intervaloDeDias(somarDias(diaRef, -(dias - 1)), diaRef);
  const pontos = montarGrade(diaRef, dias, await consumoHorario(sensor, inicio, fim, modalidade));
  return { pontos, mediaPorHora: mediaPorHoraDoDia(pontos), horasAusentes: pontos.filter((p) => p.ausente).length };
}
