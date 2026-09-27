## MAPEN Ativos &amp; Operação Inteligente

Saúde energética do equipamento e melhor horário de operação como uma única decisão

| COMPLEXIDADE INICIAL   | POSICIONAMENTO                 |
|------------------------|--------------------------------|
| Baixa a média          | Solução analítica e consultiva |

Documento de fusão | Modelo de negócio otimizado por síntese cruzada

## Documentos-base cruzados

MAPEN Energy Health + MAPEN Best Time

## Por que estes modelos foram cruzados

Nos dois documentos originais o usuário é o mesmo - engenharia de manutenção, confiabilidade, energia e operação - e os ativos são os mesmos: motores, bombas, compressores, refrigeração, climatização e transformadores. A métrica de origem também é a mesma: a série temporal de consumo específico do ativo. Energy Health responde 'este ativo está degradando?'; Best Time responde 'quando devo operá-lo?'. São duas leituras da mesma base de dados - combiná-las evita pedir ao cliente as mesmas medições em dois contratos diferentes, e permite que o estado de saúde do ativo influencie a janela de operação recomendada.

## 1. Público-alvo

| Camada     | Definição                                                                                                                                                                                            |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Primário   | Fábricas com turnos, bombeamento, refrigeração, utilidades, testes, carregamento de baterias e operações com motores, bombas, compressores, climatização e transformadores com medições disponíveis. |
| Secundário | Saneamento, mineração, pequenas e médias indústrias, geração, transmissão e instalações prediais com tarifa horária, demanda contratada ou geração solar.                                            |
| Usuário    | Engenharia de manutenção, confiabilidade, energia, planejamento, produção e operação.                                                                                                                |
| Comprador  | Gerência de manutenção, ativos, operação industrial, utilidades ou energia.                                                                                                                          |

## Necessidades do cliente

-  Saber se o equipamento continua energeticamente saudável e comparar desempenho antes e depois da manutenção.
-  Identificar tendência de aumento do consumo específico e priorizar inspeções por custo e desvio.
-  Escolher o melhor horário para uma atividade flexível e evitar novos picos de demanda.
-  Aproveitar geração local ou períodos tarifários favoráveis, com justificativa comparável entre alternativas de agenda.

## 2. Proposta de valor combinada

Mantém uma ficha de saúde energética por ativo e, a partir da mesma base de dados, recomenda as janelas de operação de menor custo e menor impacto na demanda - sem comando automático dos equipamentos, sempre com validação humana. O estado de degradação de um ativo passa a ser uma variável de entrada da recomendação de horário.

## MVP recomendado (unificado)

-  Cadastro de ativos, potência nominal, duração das atividades e horários permitidos.
-  Carga de medições, horas de funcionamento, produção, manutenção e curva de carga.
-  Linha de base individual por ativo, ficha de saúde energética e alertas estatísticos de desvio.
-  Módulo de agenda: regras de tarifa e limite de demanda informadas pelo cliente, com ranking das três melhores janelas por atividade, ajustado pelo estado de saúde do ativo.

## 3. Modelo de negócio

## Fontes de receita sugeridas

-  Assinatura por quantidade de ativos monitorados, cobrindo o módulo de saúde energética.
-  Módulo adicional de planejamento de agenda, cobrado por atividade ou carga flexível.
-  Pacote de diagnóstico do parque instalado.
-  Licença corporativa para redes de ativos semelhantes.

## Canais de aquisição e parceria

-  Parcerias com empresas de manutenção, fabricantes, integradores de automação e solares.
-  Consultorias de confiabilidade e de gestão de energia.
-  Venda consultiva para plantas com ativos repetitivos e contas de demanda relevantes.
-  Entrada por um conjunto pequeno de ativos críticos, energointensivos ou uma carga flexível recorrente.

## Estrutura principal de custos

-  Modelagem e limpeza dos dados, e biblioteca de regras por tipo de ativo.
-  Motor de otimização de agenda e configuração das regras de cada cliente.
-  Suporte técnico de contextualização operacional e validação contínua das recomendações.
-  Integrações futuras com CMMS, historiadores, IoT e sistemas de produção e energia.

## 4. Validação comercial e operacional

Piloto recomendado: Iniciar com 10 a 30 ativos semelhantes que possuam consumo, horas de operação e histórico de manutenção, incluindo ao menos uma atividade recorrente e flexível para testar o módulo de agenda comparando o horário atual com alternativas permitidas.

## Indicadores de impacto

-  Consumo específico por ativo e custo adicional associado ao desvio.
-  Quantidade de desvios confirmados e recuperação energética após manutenção.
-  Redução de picos de demanda e custo evitado por reagendamento.
-  Percentual de recomendações de horário aceitas.

## Riscos e controles

-  Mudanças de carga podem parecer degradação, e poucas medições podem reduzir a precisão.
-  Restrições operacionais incompletas podem gerar recomendações de horário inviáveis.
-  Mitigação: normalizar pela carga, sinalizar limitações dos dados, manter premissas visíveis e exigir validação humana antes de qualquer reagendamento.

## 5. Síntese do modelo fundido

| Elemento   | Definição                                                                                                                  |
|------------|----------------------------------------------------------------------------------------------------------------------------|
| Problema   | Decisões sobre a saúde e a operação dos ativos ainda dependem de dados fragmentados, análises manuais ou percepção tardia. |

| Elemento           | Definição                                                                                                                              |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Solução            | MAPEN Ativos & Operação Inteligente: passaporte de saúde energética conectado ao planejador de horários eficientes.                    |
| Valor entregue     | Conecta o diagnóstico de degradação do ativo à recomendação de quando operá-lo, em uma única base de dados.                            |
| Diferenciação      | Explicações auditáveis, uso inicial de dados existentes e expansão modular; a saúde do ativo passa a influenciar a agenda recomendada. |
| Entrada no mercado | Piloto com escopo fechado em ativos críticos ou carga flexível recorrente, economia mensurável e replicação por tipo de ativo.         |

## Ganho da fusão sobre os planos isolados

O histórico de consumo por ativo, exigido pelos dois produtos originais, é coletado uma única vez. A saúde do ativo torna-se variável de entrada do motor de agenda - algo que nenhum dos dois documentos fazia isoladamente.

## Premissas e limites

Este é um modelo conceitual derivado exclusivamente do cruzamento dos documentos de modelo de negócio MAPEN fornecidos. Preços, economia, aderência dos segmentos e capacidade de escala devem ser validados em entrevistas, pesquisa de concorrência e pilotos com dados reais. A solução inicial deve apoiar a decisão humana e explicitar a qualidade e as limitações dos dados.