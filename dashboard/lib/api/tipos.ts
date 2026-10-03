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

// M3: resultados offline (GET /modelos/resumo, /alertas, /economia). Contrato em docs/m2_seguranca_notas.md.
export type Intervalo = { inicio: string; fim: string };
export type MaeEquipamento = { equipamento: string; horas_teste: number; mae_baseline_kw: number; mae_lightgbm_kw: number; melhora_pct: number };
export type ShapFeature = { feature: string; pct: number };
export type ShapEquipamento = { equipamento: string; calendario_pct: number; historico_pct: number; feature_dominante: string | null };
export type TaxaPorTipo = { tipo: string; detectados: number; eventos: number; taxa_deteccao_pct: number };
export type DetectorSintetico = {
  detector: string;
  por_tipo: TaxaPorTipo[];
  total_detectados: number;
  total_eventos: number;
  taxa_deteccao_pct: number;
  falso_alarme_horas: number;
  horas_base: number;
  taxa_falso_alarme_pct: number;
};
export type ResumoModelos = {
  disponivel: boolean;
  rotulo: string;
  sensor_id: string | null;
  dados: {
    fonte: string;
    periodo: Intervalo;
    treino: Intervalo;
    reservado: Intervalo;
    equipamentos_no_andar: number;
    equipamentos_modelados: number;
    equipamentos_sem_carga: string[];
    linhas_minuto: number;
  } | null;
  mae: {
    unidade: string;
    horas_teste: number;
    baseline_sazonal_kw: number;
    lightgbm_kw: number;
    melhora_mediana_pct: number;
    equipamentos_total: number;
    equipamentos_lightgbm_melhor: number;
    ressalva_nowcast: string;
    por_equipamento: MaeEquipamento[];
  } | null;
  shap: {
    horas_equipamento: number;
    calendario_pct: number;
    historico_pct: number;
    por_feature: ShapFeature[];
    por_equipamento: ShapEquipamento[];
    aviso_d7: { disparado: boolean; feature: string | null; pct: number | null; limiar_pct: number; equipamentos_com_dominante: number } | null;
  } | null;
  benchmark_sintetico: { sintetico: boolean; rotulo: string; semente: number; eventos_por_tipo_por_equipamento: number; limiar_z: number; detectores: DetectorSintetico[] } | null;
  baseline_fraca: { criterio: string; semanas_completas_treino: number; equipamentos: string[] } | null;
};

export type ExplicacaoAlerta = {
  z: number;
  esperado_kw: number;
  observado_kw: number;
  janela_baseline: Intervalo;
  top_shap: { feature: string; shap: number }[] | null;
};
export type Alerta = { equipamento: string; timestamp: string; tipo: string; rotulo: string; baseline_fraca: boolean; explicacao: ExplicacaoAlerta };
export type PaginaAlertas = {
  disponivel: boolean;
  rotulo: string;
  aviso: string;
  limiar_z: number;
  periodo: Intervalo | null;
  total: number;
  limite: number;
  offset: number;
  proximo_offset: number | null;
  itens: Alerta[];
};
export type FiltroAlertas = { equipamento?: string; tipo?: string; de?: string; ate?: string; limite: number; offset: number };

export type EconomiaEquipamento = {
  equipamento: string;
  injetado_pct: number;
  recuperado_pct: number | null;
  erro_pp: number | null;
  tolerancia_pp: number;
  dentro_da_tolerancia: boolean;
  economia_pct_sem_reducao: number | null;
  baseline_fraca: boolean;
  /** Equipamentos de controle usados (so no metodo de grupo-controle). */
  controles: string[];
};
export type VereditoEconomia = {
  metodo: string;
  tolerancia_atendida: boolean;
  equipamentos: number;
  dentro_da_tolerancia: number;
  alvo_equipamento: string;
  alvo_injetado_pct: number;
  alvo_recuperado_pct: number | null;
  alvo_dentro_da_tolerancia: boolean;
  erro_abs_mediano_pp: number | null;
  erro_abs_maximo_pp: number | null;
  texto: string;
};
export type MetodoEconomia = { metodo: string; rotulo: string; veredito: VereditoEconomia; equipamentos: EconomiaEquipamento[] };
export type Economia = {
  disponivel: boolean;
  valida_metodo_nao_economia_real: boolean;
  natureza: string;
  aviso: string;
  periodo_antes: Intervalo | null;
  periodo_depois: Intervalo | null;
  reducao_sintetica: { equipamento: string; fracao_pct: number; a_partir_de: string } | null;
  /** Um item por metodo que o artefato traz (baseline sempre; grupo-controle quando o M3 o gravou). */
  metodos: MetodoEconomia[];
};

// M3: estudo de previsao do dia seguinte (GET /modelos/previsao).
export type ModeloPrevisao = {
  modelo: string;
  adotado: boolean;
  mae_agregado_kw: number | null;
  mediana_mase_reservado: number | null;
  mediana_mase_desenvolvimento: number | null;
  vitorias_vs_naive168: number | null;
  vitorias_melhor_de_todos: number;
};
export type Previsao = {
  disponivel: boolean;
  rotulo: string;
  sensor_id: string | null;
  aviso: string | null;
  horizonte_h: number | null;
  defasagem_minima_h: number | null;
  treino: Intervalo | null;
  reservado: Intervalo | null;
  dobras_walk_forward: number | null;
  referencia_mase: string | null;
  equipamentos: string[];
  sem_carga: string[];
  modelos: ModeloPrevisao[];
  decisao: {
    regra_aplicada: string;
    adotado: string;
    passaram_regra_de_ganho: string[];
    melhor_mediana: string;
    motivo: string;
  } | null;
  mase_por_equipamento: { equipamento: string; mase: Record<string, number | null> }[];
  shap_lightgbm: {
    horas: number;
    por_grupo_pct: Record<string, number | null>;
    por_feature_pct: Record<string, number | null>;
    feature_dominante: string | null;
    equipamentos_com_feature_dominante: string[];
  } | null;
  benchmark_sintetico: {
    sintetico: boolean;
    previsor: string;
    semente: number;
    eventos_por_tipo_por_equipamento: number;
    limiar_z: number;
    por_tipo: TaxaPorTipo[];
    total_detectados: number;
    total_eventos: number;
    taxa_deteccao_pct: number | null;
    falso_alarme_horas: number;
    horas_base: number;
    taxa_falso_alarme_pct: number | null;
  } | null;
  avisos: string[];
};
