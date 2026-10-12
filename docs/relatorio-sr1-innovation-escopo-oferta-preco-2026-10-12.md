---
title: "RELATÓRIO SR1 INNOVATION 2026.2"
subtitle: "MAPPEN · escopo, oferta do produto e precificação · rascunho de 12/10/2026 para revisão do grupo"
---

> **Como ler este rascunho.** Segue a estrutura do relatório SR1 da Nathália (equipe, contextualização, trajetória, escopo, aprendizados, cronograma) e acrescenta o que ele ainda não tinha: oferta do produto, mercado, precificação e riscos. Tudo que é número vem de um arquivo do repositório ou de uma execução real, citado ao lado. O que ainda é hipótese ou depende de decisão do grupo está marcado **[decidir]** ou **[?]**. Nenhum preço foi inventado: a seção 8 traz a estrutura da conta, os valores que já temos e o que falta cotar.

# 1. EQUIPE

O MAPPEN (antes MAPEN) é desenvolvido por alunos do curso de Banco de Dados e IA da Cesar School, orientados pelo professor André Luiz.

| Integrante | Período |
|---|---|
| Alex Távora | 2º período |
| Eloiza Merkl | 2º período |
| Jéssica Freitas | 2º período |
| João Rietra | 4º período |
| Lucca Lima | 2º período |
| Nathália Monteiro | 2º período |
| Wellen Mariah Lisba | 2º período |

*Fotos e e-mails: copiar do SR1 original. Responsabilidade de cada frente: ver seção 4 e o campo **[decidir]**.*

# 2. CONTEXTUALIZAÇÃO E ORIGEM DO PROJETO

As perdas de energia elétrica na distribuição são um dos principais desafios das distribuidoras brasileiras, com impacto financeiro, operacional e na qualidade do serviço. O MAPEN nasceu em Projetos 1 como uma solução para acompanhar essas perdas: comparar a energia distribuída com a consumida, calcular perdas, apontar regiões críticas e traduzir o resultado em indicadores financeiros.

Essa primeira frente (a Fase A) continua como trilha acadêmica separada. Ela gerou redflags históricas por UF e por distribuidora com dados públicos da EPE e da ANEEL, mas a validação contra um evento real e público ainda está em aberto (`TODOS.md`). Uma limitação aprendida no caminho: a série da EPE por UF é anual, não mensal, e o dado de perdas é agregado, não por cliente.

# 3. COMO O MAPEN CHEGOU AO INNOVATION E ATÉ O MAPPEN

1. **Primeira direção:** apoiar distribuidoras no monitoramento de perdas.
2. **Pesquisa e temas:** pesquisa sobre perdas e eficiência energética, e quatro temas de eficiência sugeridos com apoio de IA (energia invisível, passaporte energético, validador de projetos, planejador de janelas).
3. **Seis modelos de negócio:** Zero Waste, Energy Health, Proof, Smart Investment, Energy Intensity e Best Time. O grupo selecionou três (Zero Waste, Energy Intensity e Smart Investment).
4. **Análise cruzada:** Intelligence Platform, Plano Único, PME 360, Ativos e Operação Inteligente e Portfólio e Comprovação.
5. **Escopo escolhido, o MAPPEN:** junção de Best Time, Zero Waste e Smart Investment, com tomadas IoT como instrumento de registro e ação. A grafia mudou de MAPEN para MAPPEN após estudo de marcas e domínios. *(O repositório de código ainda usa MAPEN.)*

# 4. ESCOPO

## 4.1 O que é

Uma assinatura mensal para empresas que combina aconselhamento energético contínuo (quando usar energia, quanto custa cada horário, quais equipamentos mais pesam na conta) com sensores IoT que registram consumo com data e hora e permitem desligar ou agendar equipamentos à distância. O cliente paga pelo serviço contínuo, não pelo hardware. *Fonte: `docs/plano-pivo-iot-assinatura-2026-10-01.md`, seção 1.*

## 4.2 Quem é o cliente

Empresas (PJ). O alvo primário do SR1 são as PMEs com consumo previsível. O porte e o setor exatos **[decidir]**: PME de baixa tensão (grupo B, em especial B3) ou empresa de média tensão com tarifa horária. A escolha define sensor, tarifa e o que é carga grande demais para tomada.

## 4.3 O que está dentro

| Frente | O que entrega |
|---|---|
| A. Aconselhamento (núcleo) | Custo por horário de tarifa, ranking de equipamentos, recomendação "mover ou desligar X economiza R$ Z" |
| B. Dados e ingestão | Séries temporais (DuckDB e Parquet no piloto), ingestão de fatura, curva de carga e sensor, tratamento de falha de conexão |
| C. Datasets | Dados públicos de consumo por equipamento para prototipar, curva sintética, tarifas vigentes |
| D. Modelos | Consumo esperado por equipamento, detecção de anomalia, validação temporal sem vazamento, explicação por SHAP |
| E. Dashboard | Consumo por equipamento, custo por horário, ranking, alertas, cadastro de sensores e regras |
| F. Hardware | Piloto com sensores comerciais; placa própria com energia autônoma como requisito do produto |
| G. Referências | Revisão de artigos já existentes (sem escrever artigo novo) |
| H. Regulatório e LGPD | Regra ANEEL de ressarcimento, modalidades tarifárias, LGPD do consumo por equipamento |
| I. Dados reais iniciais | Ambiente de coleta do próprio grupo |

Ordem de entrega: **serviço primeiro, sensor depois.** O aconselhamento nasce de fatura e curva de carga (software puro) e o sensor entra onde agrega medição por equipamento e desligamento. Marcos: M0 preparação, M1 serviço sem sensor, M2 sensor no piloto, M3 economia medida, M4 prova de queda ou dano (só depois do piloto e do parecer jurídico).

## 4.4 O que está fora, por decisão registrada

1. Desligamento automático só com regra explícita do cliente, nunca em equipamento crítico, com registro de quem e de qual regra desligou.
2. Prova contra a distribuidora fica no escopo, mas depois do piloto, e não é prometida a cliente antes do parecer jurídico e regulatório.
3. Nenhuma precisão ou recall inventados. Sem rótulo real, o critério é o número de alertas que o próprio cliente corrobora.
4. Nenhum número de economia ou preço antes de medição ou cotação.
5. Hardware próprio entra primeiro no ambiente do grupo, com desligamento remoto desativado, até passar o checklist de segurança elétrica.

# 5. OFERTA DO PRODUTO

## 5.1 O que o cliente recebe

1. **Dashboard próprio** com consumo por equipamento, custo real de cada equipamento pela tarifa do horário e ranking dos que mais pesam.
2. **Recomendações** do tipo "mover ou desligar X do horário Y economiza R$ Z por mês".
3. **Alertas de anomalia com explicação** (por que o alerta disparou).
4. **Relatório mensal** com a economia observada (antes × depois da ação recomendada).
5. **Sensores:** tomada inteligente para o que cabe nela e medidor de quadro (pinça de corrente) para as cargas grandes. A cobertura da conta vira escolha de sensor por cliente.
6. **Desligamento remoto ou agendado** com regra explícita do cliente e trava para equipamento crítico.
7. **Fase posterior:** registro organizado de queda de energia e de oscilação de tensão para pedido de ressarcimento.

## 5.2 Quais dos seis modelos o produto cobre

| Modelo | Papel no MAPPEN |
|---|---|
| Zero Waste | **Núcleo.** Consumo em standby ou fora de horário, com custo em R$ |
| Smart Investment | Ranking de ações com economia estimada a partir de medição real |
| Best Time | Recomendação e agendamento de horário para carga flexível, com opt-in |
| Proof | Comprova a economia do próprio produto; ferramenta de retenção ("a assinatura se pagou") |
| Energy Health | Roadmap: histórico por equipamento e alerta de degradação |
| Energy Intensity | Roadmap: só para PME com várias unidades |

*Recomendação de lançamento (ainda para o grupo decidir): Zero Waste, alerta de anomalia e relatório mensal, mostrando Proof na prática.* Fonte: `docs/designs/mapen-assinatura-iot-tomadas.md`, seção 2.1.

## 5.3 Diferenciação

O valor está em diagnóstico, otimização e comprovação, não em ligar e desligar pelo celular. Existem tomadas inteligentes baratas com aplicativo próprio. **O levantamento de concorrentes brasileiros e dos preços deles ainda não foi feito [?]**, então o diferencial não pode ser afirmado com base em comparação. Está previsto para o estudo de mercado de 15/10.

## 5.4 Limites da oferta

1. A tomada só mede o que se liga nela. Chuveiro, motor e ar-condicionado de maior capacidade ficam no quadro e exigem medidor de quadro.
2. Medição de tomada comercial não é medidor calibrado. Serve como indício, não como prova de dano.
3. Consumo por equipamento e horário revela rotina de quem usa. Isso é dado pessoal na prática (LGPD) e entra como requisito desde o desenho.

# 6. EVIDÊNCIAS: O QUE JÁ FUNCIONA

Todos os números abaixo vêm de execuções reais (`docs/status-pivo-iot-2026-10-03.md`). O dado é o CU-BEMS, de um prédio na Tailândia, **não** um cliente nem dado brasileiro.

| Entrega | Estado |
|---|---|
| M1 · aconselhamento | Custo por faixa horária (tarifa Neoenergia PE), ranking de equipamentos e recomendações, a partir de fatura e curva de carga |
| M2 · plataforma | API com chave por empresa, cadastro de sensores e equipamentos, desligamento remoto com comando assinado e registro, dashboard com 11 telas |
| M3 · modelos | Baseline de consumo, LightGBM por equipamento, alertas com explicação, antes e depois, estudo de previsão |
| Simulador de sensor | Repete uma série real como se fosse o dispositivo, com queda de Wi-Fi, queda de energia, bateria e relógio próprio |
| Qualidade | 451 testes passando na data do status, tipagem estrita limpa |

**O que os números dizem, sem arredondar a favor:**

1. **Previsão do dia seguinte:** nenhum modelo treinado bateu o naive sazonal de 168 h (mesma hora da semana passada), que ficou com MASE mediano 0,509. Adotado o mais simples.
2. **Alertas:** 128 por z-score e 54 por LightGBM no dado real, **todos candidatos, nenhum corroborado por alguém de fora**. No benchmark sintético, 88 de 114 eventos injetados detectados.
3. **Economia:** o método foi validado com redução sintética de 15%. Com grupo de controle, 12 de 19 equipamentos ficaram dentro de ±3 pontos percentuais (sem controle, 7 de 19). Nenhum método acerta todos. **Hoje não dá para prometer um número de economia a cliente.**
4. **Painel analítico (AV1):** uma página com três vistas, referência estimada e desvio explicado, com conta independente e conferência cruzada; entregue como atividade separada.

**O que não está provado:** nada foi testado em hardware real (último suspiro, curva da bateria, deriva do relógio), não há cliente, e o benchmark de anomalias é sintético.

# 7. MERCADO E SEGMENTO

## 7.1 O que sabemos

1. **Validação de mercado:** o professor orientador afirma que é um mercado que pagaria e tem formação na área. É sinal de especialista e foi aceito como premissa de partida. Nenhuma empresa nomeada disse que paga.
2. **Tarifa.** Neoenergia PE, grupo B3 (comercial), R$/kWh sem tributos, vigência 29/04/2026 a 28/04/2027 (REH 3.583):

| Modalidade | Posto | R$/kWh |
|---|---|---|
| Convencional | único | 0,79886 |
| Branca | ponta (18h às 20h59) | 1,62479 |
| Branca | intermediário (16h às 17h59) | 1,05341 |
| Branca | fora de ponta | 0,66447 |

3. **Tarifa Branca automática:** a ANEEL abriu a Consulta Pública 46/2025, que propõe tarifa horária por padrão para baixa tensão com consumo a partir de 1 MWh/mês, a partir do fim de 2026. **É proposta, sem resolução publicada**, e o prazo não é regra vigente. Se sair, cria necessidade de medir por hora.

## 7.2 O que ainda não sabemos

1. Quantas unidades B3 com consumo a partir de 1 MWh/mês existem no Brasil e em Pernambuco: não encontrado. Sem esse número, **não há TAM, SAM ou SOM** neste relatório.
2. Concorrentes e preços de mercado (seção 5.3).
3. A fração da conta típica de uma PME que a tomada consegue enxergar.
4. Quanto do consumo é desperdício de standby. Se for pequeno, a mensalidade não se paga.

# 8. PRECIFICAÇÃO E MODELO DE ASSINATURA

**Não há preço definido nem validado.** O estudo de modelos de assinatura está no cronograma de 05/11. Esta seção entrega a estrutura da conta e o que já é possível fechar.

## 8.1 Decisões de modelo (todas em aberto, **[decidir]**)

| Decisão | Opções | Ponto de atenção |
|---|---|---|
| Hardware | (a) cliente compra; (b) comodato dentro da mensalidade; (c) kit de entrada mais assinatura | Comodato reduz a barreira de entrada, mas prende capital em estoque e aumenta o risco de churn |
| Cobrança | (a) mensalidade fixa por sensor ou unidade; (b) por faixa de consumo; (c) parte da economia medida | Parte da economia exige medição confiável, que o método atual ainda não garante em todos os equipamentos |
| Porte inicial | PME de baixa tensão ou média tensão com tarifa horária | Define a tarifa aplicável e o tipo de sensor |

Fontes de receita já descritas nos planos de negócio do grupo (modelos conceituais, sem preço): diagnóstico inicial pago, assinatura SaaS (base mais acréscimo por módulo, por instalação ou por ativo monitorado), cobrança por projeto avaliado, licença white-label, venda em lote institucional e comissão de indicação. Fonte: `docs/downloads-mapen/`.

## 8.2 A conta que o piloto precisa responder

Pergunta de unit economics: **a economia mensal medida por cliente é maior que a mensalidade mais o custo de servir?** Se não for, a assinatura não se sustenta, por melhor que seja o painel.

Custo de servir por sensor por mês (piso do preço) = hardware ÷ meses de uso (se comodato) + nuvem + suporte + instalação ÷ meses de contrato.

| Entrada | O que temos | Fonte |
|---|---|---|
| Tomada Wi-Fi com medição | R$ 59,90 a R$ 75,00 em loja (visto em 01/10); o preço de outro modelo não foi confirmado | `docs/hardware/candidatos.md` |
| Medidor de pinça (quadro) | R$ 1.350,00 (Shelly Pro 3EM-120, loja); R$ 649,90 no resultado de busca de outro modelo, não confirmado | `docs/hardware/candidatos.md` |
| Placa própria (componentes) | Subtotal R$ 114,15 para oito itens. **Incompleto:** faltam placa, sensor de corrente, fusível, regulador, conectores e caixa | `docs/hardware/proprio_bom.md` |
| Certificação (Inmetro, Anatel) | Caminho mapeado, custo **[?]** | `docs/hardware/proprio_bom.md` |
| Nuvem por sensor | **[?]** | A medir no piloto |
| Suporte por sensor | **[?]** | A definir |
| Vida útil do hardware e churn | **[?]** | Sem dado |
| Preço que o cliente aceita | **[?]** | Só o piloto responde |

## 8.3 Aritmética de referência (não é proposta de preço)

Com a tarifa branca de B3 acima, deslocar 1 kWh da ponta para o fora de ponta economiza R$ 1,62479 − R$ 0,66447 = **R$ 0,96032** (sem tributos). Eliminar 1 kWh de standby na tarifa convencional economiza R$ 0,79886. Para uma mensalidade M qualquer, a economia mensal mínima que o cliente precisa ter é M, o que equivale a:

| Mensalidade M (valor de referência para a conta) | kWh/mês a deslocar da ponta | kWh/mês de standby a eliminar |
|---|---|---|
| R$ 50 | 52,1 | 62,6 |
| R$ 100 | 104,1 | 125,2 |
| R$ 200 | 208,3 | 250,4 |

Os três valores de M são só para ilustrar a conta, não sugerem preço. A tabela mostra uma condição necessária e não suficiente: a economia precisa existir, ser medida e ser atribuída ao serviço. Fora a tarifa branca, deslocar carga não economiza nada na tarifa convencional (preço único); só eliminar consumo economiza.

## 8.4 Como fechar a precificação

1. Cotar 3 a 5 sensores e concluir a lista de materiais da placa (frente F).
2. Medir custo de nuvem no piloto e definir suporte.
3. Levantar concorrentes brasileiros e preços (seção 5.3).
4. Perguntar ao professor orientador qual forma de cobrança considera viável (mensalidade fixa ou parte da economia).
5. Piloto com empresas nomeadas: medir economia observada e perguntar "pagaria?" e "quanto?". Usar de graça não é pagar.

# 9. RISCOS E LIMITES

1. **Demanda sem comprador nomeado.** O maior risco aberto.
2. **Cobertura da medição.** A tomada pode perder a maior parte do gasto, que costuma estar no quadro.
3. **Economia pode ser pequena.** Standby costuma ser fração modesta da conta **[?]**.
4. **Concorrência** ainda não mapeada.
5. **Hardware e regulação.** Certificação, segurança elétrica, garantia, logística e suporte: o grupo hoje é 100% software e dados.
6. **LGPD.** Consumo por equipamento revela rotina.
7. **Qualidade do dado em rede doméstica ou de PME.** Wi-Fi cai, relógio deriva, sensor reinicia.
8. **Prova contra a distribuidora.** Um produto que ajuda o cliente a cobrar da Neoenergia é adversarial a ela, o que conflita com tratá-la como canal ou parceira. As duas posições não cabem juntas **[decidir]**. A regra vigente de ressarcimento (REN 1000/2021, conforme os docs do grupo) ainda precisa ser lida no texto oficial.
9. **Gargalo não é código.** É hardware (compra, certificação, instalação), empresa-piloto e decisão do grupo.

# 10. PRINCIPAIS APRENDIZADOS E PRÓXIMOS PASSOS

**Aprendizados dos primeiros 30 dias:**

1. O software do serviço roda de ponta a ponta sobre dado público real, e os números mostram com honestidade o que ainda não está provado (seção 6).
2. O caminho crítico não é código: é hardware próprio, empresa de teste e decisões do grupo.
3. O baseline mais simples (mesma hora da semana passada) superou os modelos treinados. Isso reduz a complexidade do primeiro produto.
4. Houve contato com membros da Neoenergia para entender o processo energético da região.

**Decisões que dependem do grupo e do professor orientador:**

1. Donos de cada frente e quantas pessoas existem no grupo.
2. Tipo de empresa e de equipamento em mente (define sensor e tarifa).
3. Ambiente do grupo para os primeiros dados reais (casa, laboratório) e equipamentos a medir.
4. Forma de cobrança (seção 8.1).
5. Neoenergia: parceira ou contraparte (seção 9, item 8).
6. Nome do produto e confirmação do MAPPEN como marca.

**Próximos passos, em ordem:**

1. Cotar sensores e fechar a lista de materiais (peças de prazo longo primeiro).
2. Escolher o ambiente de coleta e ligar o primeiro sensor, só com recomendação (desligamento remoto desativado).
3. Rodar o mesmo ciclo de modelos em dado medido pelo próprio grupo.
4. Ler a regra da ANEEL sobre ressarcimento antes de prometer qualquer prova a cliente.
5. Levantar concorrentes e fechar o estudo de mercado.

As evidências, discussões e estudos estão na pasta `docs/` do repositório e no drive da equipe.

# 11. CRONOGRAMA ATÉ O SR2

O cronograma do SR1 original, com o estado conforme os arquivos do repositório. Onde não há evidência, está **a confirmar pelo grupo**.

| Data | Entrega | Estado |
|---|---|---|
| 01/10 | Entrega do relatório SR1 | Entregue |
| 08/10 | Discussão com o professor orientador e escolha definitiva da ideia | A confirmar pelo grupo |
| 15/10 | Aprofundamento no projeto e estudo de mercado | Escopo e oferta descritos neste relatório; concorrentes e tamanho de mercado pendentes |
| 22/10 | Abertura de termos | A confirmar pelo grupo |
| 29/10 | Estudo sobre sensores e IoTs | Levantamento inicial feito (candidatos comerciais e lista de materiais da placa) |
| 05/11 | Estudo sobre modelos de assinatura | Estrutura da conta na seção 8; faltam cotações e piloto |
| 12/11 | Aprofundamento em LGPD | Citada nos riscos; estudo dedicado ainda não existe |
| 19/11 | Fechamento das entregas para o SR2 | Pendente |
| 26/11 | Entregas finais SR2 | Pendente |
