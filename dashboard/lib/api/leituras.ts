import { ler } from "./cliente";
import type { ConsumoAgora, Configuracao, Custo, Economia, Equipamento, Evento, FiltroAlertas, PaginaAlertas, PontoHorario, Ranking, Regra, ResumoModelos, Sensor } from "./tipos";

const id = encodeURIComponent;
/** `+` do offset (-03:00 nao tem, mas +HH:MM teria) precisa ir como %2B: encodeURIComponent cuida. */
const periodo = (inicio: string, fim: string, modalidade: string): string =>
  `inicio=${id(inicio)}&fim=${id(fim)}&modalidade=${id(modalidade)}`;

export const listarSensores = (): Promise<Sensor[]> => ler("/sensores");
export const listarEquipamentos = (): Promise<Equipamento[]> => ler("/equipamentos");
export const listarRegras = (): Promise<Regra[]> => ler("/regras");
export const listarEventos = (limite = 100): Promise<Evento[]> => ler(`/eventos?limite=${limite}`);
export const obterConfiguracao = (): Promise<Configuracao> => ler("/configuracao");

export const consumoAgora = (sensor: string): Promise<ConsumoAgora> => ler(`/sensores/${id(sensor)}/consumo-agora`);
export const custoPorFaixa = (sensor: string, inicio: string, fim: string, modalidade: string): Promise<Custo[]> =>
  ler(`/sensores/${id(sensor)}/custo?${periodo(inicio, fim, modalidade)}`);
export const ranking = (sensor: string, inicio: string, fim: string, modalidade: string, n = 10): Promise<Ranking[]> =>
  ler(`/sensores/${id(sensor)}/ranking?${periodo(inicio, fim, modalidade)}&n=${n}`);
export const consumoHorario = (sensor: string, inicio: string, fim: string, modalidade: string): Promise<PontoHorario[]> =>
  ler(`/consumo/horario?sensor_id=${id(sensor)}&${periodo(inicio, fim, modalidade)}`);

/** Query so com os filtros presentes; `+` do fuso vai como %2B. */
const consultaAlertas = (f: FiltroAlertas): string => {
  const p: [string, string][] = [["limite", String(f.limite)], ["offset", String(f.offset)]];
  if (f.equipamento !== undefined) p.push(["equipamento", f.equipamento]);
  if (f.tipo !== undefined) p.push(["tipo", f.tipo]);
  if (f.de !== undefined) p.push(["de", f.de]);
  if (f.ate !== undefined) p.push(["ate", f.ate]);
  return p.map(([k, v]) => `${k}=${id(v)}`).join("&");
};

export const resumoModelos = (): Promise<ResumoModelos> => ler("/modelos/resumo");
export const listarAlertas = (filtro: FiltroAlertas): Promise<PaginaAlertas> => ler(`/alertas?${consultaAlertas(filtro)}`);
export const economiaM3 = (): Promise<Economia> => ler("/economia");
