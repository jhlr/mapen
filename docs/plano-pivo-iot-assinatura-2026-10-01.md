# Pivô MAPEN: assinatura de sensores IoT + aconselhamento energético — doc de planejamento (2026-10-01)

> Para a Natália e o professor. Este documento é de **escopo e prioridade**, não um plano de execução fixo. As decisões de produto abaixo já foram tomadas na conversa de 2026-09-30/10-01; o que sobra é o sim/não/quando e as perguntas abertas (seção 8). Contexto e justificativa em `docs/designs/mapen-assinatura-iot-tomadas.md` (v3, commit `1120d19`).

## 1. O que é

Uma assinatura mensal para empresas (PJ) que combina dois ingredientes: aconselhamento energético contínuo (quando usar energia, quanto custa cada horário, quais equipamentos mais pesam na conta) e uma família de sensores IoT (tomada inteligente para o que cabe nela, medidor de quadro para cargas grandes) que registra consumo com data e hora e permite desligar ou agendar equipamentos à distância. O cliente paga pelo serviço contínuo, não pelo hardware. Mais adiante, os mesmos registros podem servir de prova de queda de energia e dano a aparelhos num pedido de ressarcimento à distribuidora.

## 2. Quem faz o quê

Donos **em aberto** por decisão do grupo. Cada frente da seção 4 tem o campo "dono: a definir".

## 3. Onde aparece para o usuário final

1. **Dashboard web** próprio: consumo por equipamento, custo por horário de tarifa, ranking de equipamentos, alertas, cadastro de sensores e regras de desligamento.
2. **Relatório mensal** ao cliente: economia observada e recomendações.
3. **Alertas** de anomalia com explicação.
4. Fase posterior: relatório de evento elétrico (queda, subtensão, sobretensão) para ressarcimento.

## 4. Mecanismo central e frentes de trabalho

Ordem de entrega decidida: **serviço primeiro, sensor depois**. O aconselhamento nasce de fatura e curva de carga (software puro, testável com empresa real sem esperar hardware); o sensor entra onde agrega medição por equipamento e desligamento.

| Frente | O que entrega | Dono | Esforço |
|---|---|---|---|
| **A. Aconselhamento (núcleo)** | Custo por horário de tarifa, ranking de equipamentos, recomendação "mover/desligar X economiza R$ Z". Entrada: fatura e curva de carga do cliente | a definir | M |
| **B. Databases / ingestão** | Esquema de séries temporais (DuckDB/Parquet no piloto, padrão do repo), ingestão de fatura/curva (arquivo) e de sensor (MQTT ou API), reindexação de calendário para lidar com falha de conexão | a definir | M |
| **C. Datasets** | (1) datasets públicos de consumo por equipamento para prototipar modelos (a levantar; **licença e adequação ao Brasil a verificar**); (2) curva sintética com tarifa horária; (3) tarifas vigentes da Neoenergia PE (resolução ANEEL) | a definir | S a M |
| **D. Modelos de ML** | Baseline de consumo esperado por equipamento/hora (regressão, resíduo = anomalia), detecção de ociosidade, recomendação de janela; validação temporal sem vazamento; explicação por SHAP | a definir | M |
| **E. Dashboard** | Next.js sobre a base da frente B; telas da seção 3 | a definir | M |
| **F. Hardware** | Piloto com sensores comerciais abertos (tomada + medidor de quadro; modelos, preço, certificação e corrente máxima a levantar). **Hardware próprio com energia autônoma** (decisão do grupo, 2026-10-01): placa com RTC, memória local e supercapacitor/bateria, para registrar horário e oscilações de carga independente de conexão e de rede elétrica. É requisito do produto, não exploração: sem ele, queda de energia e queda de Wi-Fi não se distinguem. Sensores comerciais ficam como atalho de M1/M2 | a definir | M a L |
| **G. Referências (artigos)** | Revisão dos artigos já existentes (desagregação de carga, detecção de anomalia em consumo, resposta à demanda, M&V) como base de método e baseline de comparação. **Não inclui escrever artigo novo** | a definir | S |
| **H. Regulatório e LGPD** | Leitura da regra ANEEL vigente de ressarcimento por dano elétrico, modalidades tarifárias, LGPD do consumo por equipamento (revela rotina), parecer sobre valor probatório | a definir | S a M |
| **I. Validação de demanda** | Nomear empresas-piloto (contatos via professor), entrevistas "pagaria? quanto?", critério de sinal fraco/forte do design de 11/09 | a definir | S |

### Marcos

1. **M0, preparação:** cotação de 3 a 5 sensores, 1 a 2 contatos de empresa, tarifa vigente levantada. (Frentes C, F, H, I.)
2. **M1, serviço sem sensor:** fatura/curva de uma empresa → custo por horário → ranking e recomendação em DuckDB e um gráfico. (A, B, C.)
3. **M2, sensor no piloto:** 1 sensor → ingestão → DuckDB → gráfico, depois piloto em 1 empresa com tomada e, se couber, medidor de quadro. Inclui desligamento remoto com regra explícita do cliente. (B, D, E, F.)
4. **M3, economia medida:** relatório antes × depois com a pergunta "pagaria? quanto?". (D, E, I.)
5. **M4, prova de queda/dano:** só após o piloto e depois do parecer da frente H. M1 a M3 apenas registram tensão e eventos com carimbo de tempo local, para não perder dado.

Caminho crítico: **hardware (F) e empresa-piloto (I)**. As frentes de código não bloqueiam o plano.

## 5. Estrutura mínima proposta (MVP)

Entidades: `empresa`, `unidade`, `sensor` (tipo: tomada/quadro; modelo; carga monitorada), `equipamento`, `leitura` (instante, potência, tensão, kWh), `tarifa` (modalidade, faixa horária, valor), `regra_desligamento` (equipamento, horário, quem autorizou), `evento` (queda, subtensão, desligamento executado, origem da ordem), `recomendacao`.

## 6. Decisões sensíveis já tomadas (registradas de propósito)

1. **Desligamento automático só com regra explícita do cliente**, nunca em equipamento crítico, com registro de quem/qual regra desligou. Não é esquecimento: é trava de segurança.
2. **A prova contra distribuidora fica no escopo, mas depois do piloto** e sem prometê-la a cliente antes do parecer da frente H. Foi conselho do professor manter no escopo.
3. **Não reportar precisão/recall inventados.** Sem rótulo real, o critério é nº de alertas corroborados pelo cliente (mesma regra do `crisp_dm.md`).
4. **Sem número de economia ou preço antes de medição ou cotação.** Campos `[?]` permanecem assim até haver fonte.
5. **Contexto:** o grupo está em pré-incubação e pivotando por falta de tração; o plano otimiza para aprender rápido e barato, não para faturar.

## 7. Infraestrutura existente que o plano reaproveita

| Componente | Onde | O que reaproveita |
|---|---|---|
| Baseline z-score sazonal | `src/redflags_perdas.py` (`perda_dist()`) | Primeiro detector de anomalia por equipamento; limiar precisa ser recalibrado (calibrado em série agregada longa) |
| Plano do modelo 3.2 (regressão do esperado, resíduo = anomalia) | `docs/modelagem_redflags.md`, `docs/crisp_dm.md` | Mesma lógica de modelo; aqui o dado é denso, o boosting faz mais sentido |
| Stack Python | `pyproject.toml` (pandas, duckdb, pyarrow, xgboost, lightgbm, scikit-learn); `shap` ainda não está nas dependências | Frentes B e D; adicionar `shap` |
| Armazenamento Parquet/DuckDB | `data/consumo/*` (`ons`, `epe`, `samp`, `samp_balanco`) | Padrão de pasta e formato para novas séries |
| Script de download reutilizável | `src/ons_load.py` | Padrão para ingestão de dataset público |
| Gráficos de análise | `src/plot_perdas_ano.py`, `src/plot_br_consumo.py` | Base para os primeiros gráficos de M1 e M2 |
| Dados públicos de consumo | `data/consumo/epe`, `data/consumo/ons` | Só contexto e benchmark por UF/classe. **Não servem para treinar modelo por equipamento** |
| Decisões D4 (calendário completo), D6, D7 (SHAP sem tautologia), T2 (split temporal) | CEO review de 2026-09-11, handoff do repo | Aplicam-se diretamente à série de sensor, onde o buraco de conexão é pior que nas distribuidoras |
| Pendência de validação | `TODOS.md` | Fase A continua trilha separada, entrega acadêmica combinada |

## 8. Perguntas abertas para a Natália e o professor

1. **Donos de cada frente** (seção 4), e quantas pessoas existem no grupo.
2. **Que tipo de empresa e equipamento** o professor tem em mente? Define sensor, tarifa e o que é "carga grande" demais para tomada.
3. **Contatos para o piloto:** o professor indica 1 ou 2 empresas?
4. **Forma de cobrança:** mensalidade fixa por sensor/unidade, faixa de consumo ou parte da economia?
5. **Neoenergia:** canal/parceira (hipótese de 2.3 do design) ou contraparte adversarial pela prova de dano? As duas posições não cabem juntas, e isso afeta o Projeto 4.
6. **Hardware próprio:** qual autonomia mínima de registro sem rede elétrica o produto precisa (minutos/horas), supercapacitor ou bateria de lítio (segurança), e quem do grupo domina eletrônica embarcada e certificação Anatel/Inmetro?
7. **Quais datasets públicos** o grupo já conhece e podem entrar na frente C, e quais artigos pré-existentes entram em G.
8. **Parecer jurídico:** quem tem acesso a uma pessoa que entenda de regulação do consumidor?
9. **Fase A (redflags de perda):** segue como trilha acadêmica separada, como proposto, ou é absorvida na nova narrativa?

## 9. Esforço estimado (ordem de grandeza)

S a M para cada frente de software (A, B, C, D, E); M a L para hardware (F), porque compra, certificação e instalação não dependem da velocidade de código; S para G, H e I, mas H e I dependem de terceiros (jurídico, empresas). O total é decidido pelo caminho crítico (hardware e empresa-piloto), não pela soma das frentes de código.

## 10. O que este plano deliberadamente NÃO resolve

1. Nome do produto, preço e unit economics (sem cotação nem medição).
2. Donos e datas (sem calendário; os marcos são ordem, não prazo).
3. Qual dataset público específico usar e se a licença permite uso comercial.
4. Valor jurídico real da medição de uma tomada comercial.
5. Modelagem final de ML: só direção (baseline de consumo esperado, resíduo, SHAP), sem escolha de features.
6. Telas do dashboard além da lista da seção 3.
7. Integração com a Neoenergia (canal ou contraparte), por decisão pendente.
8. Escrita de artigo novo: os artigos entram só como referência.
