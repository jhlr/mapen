// Contratos JSON da API FastAPI (espelham interface/api/esquemas.py). Todo instante tem fuso.
export type Sensor = { id: string; unidade_id: string; nome: string };
export type Equipamento = { id: string; sensor_id: string; nome: string; critico: boolean };
export type Regra = {
  id: string;
  equipamento_id: string;
  cron: string;
  ativo: boolean;
  autorizado_por: string;
  criado_em: string;
};
export type ConsumoAgora = {
  sensor_id: string;
  ts_referencia: string;
  potencia_w: number;
  kwh_dia: number;
  por_equipamento: { equipamento: string; kwh: number }[];
};
export type Custo = { equipamento: string; faixa: string; kwh: number; custo_rs: number };
export type Ranking = { equipamento: string; kwh: number; custo_rs: number; pct_ausente: number };
export type PontoHorario = { hora: string; kw: number; faixa: string };
export type Configuracao = { desligamento_remoto_habilitado: boolean };
export type Evento = {
  id: string;
  ts: string;
  tipo: string;
  sensor_id: string | null;
  equipamento_id: string | null;
  origem: string;
  regra_id: string | null;
  autorizado_por: string | null;
  payload: Record<string, string>;
};

export type Acao = "desligar" | "ligar";
export type ComandoIn = {
  device_id: string;
  acao: Acao;
  nonce: string;
  emitido_em: string;
  validade: string;
  assinatura: string;
};
/** Sem autorizado_por: a API usa o nome do principal da chave. */
export type DesligamentoIn = {
  equipamento_id: string;
  comando: ComandoIn;
  origem: string;
  regra_id: string | null;
};
export type DesligamentoOut = { aceito: boolean; motivo: string | null; evento_id: string };
export type EquipamentoIn = { sensor_id: string; nome: string; critico: boolean };
export type RegraIn = { equipamento_id: string; cron: string; ativo: boolean };
