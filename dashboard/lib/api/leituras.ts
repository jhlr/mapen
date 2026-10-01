import { ler } from "./cliente";
import type { ConsumoAgora, Custo, Equipamento, Evento, Ranking, Regra, Sensor } from "./tipos";

const id = encodeURIComponent;
const periodo = (inicio: string, fim: string, modalidade: string): string =>
  `inicio=${inicio}&fim=${fim}&modalidade=${modalidade}`;

export const listarSensores = (empresa: string): Promise<Sensor[]> => ler("/sensores", empresa);
export const listarEquipamentos = (empresa: string): Promise<Equipamento[]> => ler("/equipamentos", empresa);
export const listarRegras = (empresa: string): Promise<Regra[]> => ler("/regras", empresa);
export const listarEventos = (empresa: string, limite = 100): Promise<Evento[]> =>
  ler(`/eventos?limite=${limite}`, empresa);

export const consumoAgora = (empresa: string, sensor: string): Promise<ConsumoAgora> =>
  ler(`/sensores/${id(sensor)}/consumo-agora`, empresa);
export const custoPorFaixa = (
  empresa: string, sensor: string, inicio: string, fim: string, modalidade: string,
): Promise<Custo[]> => ler(`/sensores/${id(sensor)}/custo?${periodo(inicio, fim, modalidade)}`, empresa);
export const ranking = (
  empresa: string, sensor: string, inicio: string, fim: string, modalidade: string, n = 10,
): Promise<Ranking[]> => ler(`/sensores/${id(sensor)}/ranking?${periodo(inicio, fim, modalidade)}&n=${n}`, empresa);
