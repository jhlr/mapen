export const MOTIVOS: Record<string, string> = {
  assinatura_invalida: "Assinatura HMAC inválida (ou sensor sem chave provisionada na API).",
  comando_malformado: "O comando está malformado (campo vazio ou fora do formato).",
  dispositivo_divergente: "O device_id do comando não é o sensor deste equipamento.",
  ttl_excessivo: "A validade passa de 60 s depois da emissão.",
  emissao_futura: "A emissão está mais de 5 s no futuro (confira o relógio de quem assinou).",
  validade_vencida: "O comando passou da validade.",
  nonce_repetido: "Esse nonce já foi usado; cada comando precisa de um nonce novo.",
  regra_invalida: "A regra informada não está ativa ou não é deste equipamento.",
  equipamento_critico: "Equipamento marcado como crítico: nunca é desligado remotamente.",
  sem_autorizacao: "O comando não tem uma pessoa autorizada associada.",
  desligamento_remoto_desabilitado:
    "O desligamento remoto está desativado na API (modo só recomendação). Nada foi enviado ao relé.",
  falha_atuador: "O atuador não respondeu; o relé pode não ter mudado de estado.",
  equipamento_desconhecido: "Equipamento não encontrado nesta empresa.",
};
export const explicarMotivo = (m: string): string => MOTIVOS[m] ?? m;
