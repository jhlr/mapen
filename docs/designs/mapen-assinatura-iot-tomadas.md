# MAPEN — assinatura mensal de tomadas inteligentes (IoT) + dashboard próprio

**Data:** 2026-09-30
**Status:** RASCUNHO v3 (superado em hardware, demanda e segurança por `docs/plano-pivo-iot-assinatura-2026-10-01.md` e `docs/specs/spec-pivo-iot-assinatura-2026-10-01.md`) para revisão da Natália (nada aqui está decidido). A seção 1.1 incorpora o retorno do professor e prevalece sobre o resto onde houver conflito.
**Origem:** sugestão do professor — pivotar para uma assinatura mensal de um sistema IoT de tomadas inteligentes, com dashboard próprio de gerenciamento e otimização.
**Docs de base:** `contexto_mapen.md`, `designs/mapen-negocio-ou-nao.md` (03/09), `designs/eficiencia-energetica-pf-pj.md` (11/09), `modelos_negocio_eficiencia_energetica.md` (17/09), `oportunidades_negocio_energia.md`, `crisp_dm.md`, `modelagem_redflags.md`.

---

## 1. A ideia em 5 linhas

1. O cliente (PF ou PME) pluga tomadas inteligentes com medição de potência/energia nos equipamentos que quer acompanhar.
2. As tomadas enviam kW/kWh em intervalos curtos para a nossa nuvem.
3. O MAPEN mostra num dashboard próprio onde, quando e quanto cada equipamento consome, e o que está sendo desperdiçado.
4. O sistema recomenda (e, numa fase posterior, executa com autorização) ações de otimização: desligar o que está ocioso, mover cargas flexíveis de horário, avisar de anomalia.
5. O cliente paga mensalidade. O valor vendido é o serviço contínuo (monitoramento + diagnóstico + otimização), não o hardware.

## 1.1. Atualização (retorno do professor, mesmo dia)

Três esclarecimentos que mudam o desenho. Onde conflitam com o texto abaixo, **vale esta seção**.

1. **Produto central = aconselhamento energético para empresas (PJ):** quando usar, como o preço da energia varia por horário, quais equipamentos gastam mais. O professor disse que é um mercado que pagaria e tem formação na área para afirmar isso. Isso é um sinal de especialista, **não** um comprador nomeado dizendo que paga: sobe a confiança no mercado, mas o critério de "sinal forte" do design de 11/09 (pessoa real que pagaria) continua aberto.
2. **A tomada é o instrumento de registro e de ação:** guarda consumo com data/hora e permite **desligamento remoto ou automatizado**. Logo o comando de relé entra no núcleo, não na "fase 3". Continuam valendo as travas de segurança (seção 3): nunca em equipamento crítico, regra explícita do cliente, confirmação antes de qualquer automação nova, e registro de quem/que regra desligou.
3. **Segundo uso: prova contra a distribuidora.** O log de tensão e de falta de energia com carimbo de tempo serviria para comprovar quedas e danos a aparelhos num pedido de ressarcimento.

### 1.1.1. Preço da energia por horário (o coração do aconselhamento)

- Empresas atendidas em média tensão (grupo A) costumam ter tarifa com **ponta e fora de ponta** e demanda contratada; baixa tensão tem opção de **tarifa branca**. `[?]` confirmar modalidades e valores da Neoenergia PE (fonte: resolução tarifária ANEEL vigente) antes de qualquer cálculo em R$.
- O serviço vira: (a) curva de consumo por equipamento × tarifa por horário = custo real de cada equipamento; (b) lista dos equipamentos mais caros; (c) recomendação "mover/desligar X do horário Y economiza R$ Z/mês"; (d) agendamento/desligamento automático via tomada para o que for flexível.
- Isso é o modelo **Best Time** + **Zero Waste** + **Smart Investment** juntos, e passam a ser o núcleo. Energy Health e Energy Intensity seguem no roadmap.
- Limite: a tomada só controla o que cabe nela. Carga de potência alta ligada no quadro (motor, ar de maior capacidade, chuveiro) exige contator/medidor de quadro, não tomada. `[?]` perguntar ao professor que tipo de empresa e equipamento ele tem em mente.

### 1.1.2. Comprovar queda de energia e dano a aparelho

O que a tomada pode registrar: tensão e potência por amostra, momentos de sumiço e retorno de energia, sobretensão/subtensão.

O que precisa ser verificado antes de prometer isso a qualquer cliente:
- **Regra vigente de ressarcimento por dano elétrico** (ANEEL, REN 1000/2021 pelo que lembro, com prazo para o consumidor pedir e prazo para a distribuidora responder). `[?]` ler o texto atual; os prazos e o ônus da prova mudam o valor da evidência.
- **Valor probatório:** medição de tomada comercial não é medidor calibrado. Pode servir como indício e para organizar o pedido, mas a distribuidora tem os próprios registros e pode contestar. Precisa de: relógio sincronizado (NTP), registro que não possa ser editado depois (hash/assinatura dos blocos de log), calibração conhecida do sensor de tensão.
- **Queda × Wi-Fi caído:** na queda de energia o roteador também cai. Tomada offline não prova queda. Solução técnica: guardar dado localmente na tomada (ou bateria/supercapacitor para um último pacote) e enviar ao voltar, com o carimbo do próprio dispositivo.
- **Dano ao aparelho:** o log mostra o evento elétrico, não que o aparelho queimou por causa dele. Prova de dano continua exigindo laudo.
- **Conflito estratégico com a Neoenergia:** um produto que ajuda o cliente a cobrar da distribuidora é adversarial a ela. Isso contradiz a hipótese da seção 2.3 de tratar a distribuidora como canal. As duas posições não cabem juntas; o grupo precisa escolher qual contar, e isso afeta o desafio do Projeto 4. Registrado como decisão pendente na seção 7.
- **Elo com a Fase A:** eventos de tensão/queda agregados de muitos clientes seriam um dado de qualidade de fornecimento por região, que hoje não existe em dado aberto no MAPEN. Hipótese de longo prazo, não promessa.

## 1.2. Esclarecimentos do grupo (sobre a primeira revisão de viabilidade)

1. **Fase:** pré-incubação, pivotando por falta de tração. O critério de sucesso é aprender rápido e barato, não faturar. O piloto da seção 6 já está dimensionado para isso.
2. **Sensores, não só tomada:** a oferta é uma família de sensores IoT. Tomada inteligente para o que cabe nela; medidor de quadro (ex.: pinça de corrente) para as cargas grandes. Cobertura da conta deixa de ser risco estrutural e vira **escolha de sensor por cliente**. `[?]` levantar custo e certificação do sensor de quadro.
3. **Assinatura por serviço, não por hardware:** o valor vendido é o aconselhamento contínuo (horário, tarifa, equipamentos caros, otimização), que vai além do que um sensor mostra. Fatura e curva de carga já existentes também alimentam o serviço; o sensor entra onde ele agrega medição por equipamento e controle.
4. **Prova contra a distribuidora fica no escopo**, por orientação do professor, tratada como módulo próprio com peso jurídico/regulatório (seção 1.1.2). Antes de vender: ler a regra vigente, definir o padrão de evidência e checar com quem entende de direito do consumidor/regulação.
5. **Capacidade de execução:** o gargalo esperado não é código. É hardware (compra, certificação, instalação), empresas-piloto e decisão do grupo. O risco 9 da seção 5 deve ser lido assim.

## 2. Por que isso encaixa no que já temos

Em 11/09 o design da Fase D registrou que o maior bloqueio para qualquer produto de eficiência era **acesso a dado**: nenhuma leitura por equipamento/consumidor existe no MAPEN, e a Approach B (desagregação de consumo) só entraria em execução se duas condições se resolvessem: (1) demanda validada e (2) um caminho real de acesso a dado, citando literalmente "hardware IoT próprio" como uma das rotas possíveis.

A sugestão do professor resolve a condição 2: **o hardware próprio gera o dado**. A condição 1 (alguém pagar) continua sem evidência. Isso precisa ficar explícito para a revisão: a ideia remove o bloqueio de dado, não o de demanda.

### 2.1. O que dos 6 modelos de negócio (17/09) o produto cobre

| Modelo | Papel na versão com tomadas | Dado necessário | Estado |
|---|---|---|---|
| **Zero Waste** (energia invisível) | **Núcleo do produto.** Consumo em standby/fora de horário por tomada, com custo em R$ | Potência por tomada em intervalos curtos (a tomada entrega isso nativamente) | Antes dependia de curva de carga que não tínhamos; agora a própria tomada fornece |
| **Energy Health** (passaporte de equipamento) | Histórico de potência por equipamento, alerta de degradação (ex.: geladeira passando a consumir mais) | Série por equipamento, semanas a meses | Viável após acumular histórico |
| **Smart Investment** (validador de projetos) | Ranking de ações (trocar equipamento, desligar, mudar horário) com economia estimada a partir de medição real, não de questionário | Medição + tarifa | Melhora muito: o ranking passa a usar dado medido |
| **Proof** (M&V) | Comprova a economia do próprio produto (antes × depois da ação recomendada). Também resolve o ovo-e-galinha antigo: a intervenção é nossa, não precisamos de ESCO parceira | Baseline por equipamento | Boa ferramenta de retenção: "a assinatura se pagou" |
| **Energy Intensity** | Comparar unidades (filiais, salas) numa conta PME com várias unidades | Consumo por unidade + denominador operacional | Fase posterior, só PME multi-unidade |
| **Best Time** (janelas) | Recomendar/agendar horário de carga flexível (carregador, bomba, ar, boiler). A tomada tem relé, então o comando existe | Tarifa horária + restrições | Fase 3, com opt-in explícito (o doc de temas pedia "sem comando automático no 1º estágio") |

Recomendação de escopo (para discutir): lançar com **Zero Waste + alerta de anomalia + relatório mensal**, mostrar **Proof** na prática, e deixar Energy Health, Best Time e Energy Intensity como roadmap.

### 2.2. O que do código/pipeline da Fase A se reaproveita

Honestidade: os modelos da Fase A rodam sobre dado agregado de distribuidora (SAMP-Balanço) e UF (EPE). Os dados não servem para esse produto. Reaproveita-se o **método e o código de apoio**.

| Ativo existente | Reuso no produto de tomadas |
|---|---|
| Baseline z-score sazonal (`src/redflags_perdas.py`) | Primeiro detector de anomalia por tomada. Já adiantei a ressalva do design de 11/09: o limiar foi calibrado em série longa e agregada, precisa ser recalibrado para consumo de um equipamento |
| Modelo 3.2 (regressão do esperado, resíduo = anomalia; XGBoost/LightGBM) | Mesma lógica: prever o consumo esperado da tomada (hora, dia da semana, feriado, temperatura) e sinalizar o resíduo. Aqui o dado é denso, então o boosting faz mais sentido do que no nível UF |
| Validação temporal walk-forward + teste de leakage (T2) | Aplica-se igual; é o que impede o modelo de "ver o futuro" |
| Reindexação a calendário completo (D4) | **Mais crítico ainda**: tomada Wi-Fi cai, fica offline, perde pacote. Um `shift()` posicional sobre buracos gera lag errado sem erro visível, exatamente o bug que o D4 já mapeou nas distribuidoras |
| SHAP + checagem de tautologia (D7) | Explicar por que o alerta disparou ("fora do horário usual", "subiu X% vs. baseline") é requisito de produto, não só de avaliação |
| Critérios de sucesso por corroboração, não por precisão inventada (`crisp_dm.md`) | Mesma disciplina: sem rótulo real, não reportar precisão/recall estimado |
| Dados públicos (EPE consumo por classe/UF, tarifas ANEEL) | Contexto e benchmark ("seu consumo vs. média da sua UF/classe"), cálculo de R$ a partir da tarifa. Papel secundário |

Fase A (perdas, lado da distribuidora) **não é descartada**, mas passa a ser uma trilha separada: a entrega acadêmica já combinada continua e não compete com o protótipo de tomadas (decisão D5 da CEO review segue valendo).

### 2.3. Relação com Neoenergia

Hipótese, não fato: uma distribuidora pode ser **canal ou parceiro** (programas de eficiência energética que as distribuidoras são obrigadas a financiar; resposta à demanda; tarifa branca), em vez de concorrente. Precisa ser verificado com alguém de dentro e com a regulação vigente antes de entrar em qualquer apresentação. Não tem nome nem confirmação até agora.

## 3. Como o sistema funciona (arquitetura mínima)

```
tomada (medição + relé)  ->  MQTT / API do fabricante  ->  ingestão  ->  banco de séries temporais
                                                                           |
                                          modelos (baseline, anomalia, ociosidade)  ->  dashboard web  ->  alertas / relatório
                                                                           |
                                                           (fase 3) comando de relé com opt-in
```

- **Hardware:** para o piloto, usar tomadas comerciais abertas/configuráveis (ex.: famílias com firmware Tasmota/ESPHome, ou Shelly/Tuya) em vez de projetar hardware. Para validar: modelos, preço no Brasil, certificação Anatel/Inmetro, corrente máxima e tomada padrão NBR 14136.
- **Ingestão:** MQTT ou API do fabricante; preferir o caminho que não prenda ao fabricante.
- **Armazenamento:** DuckDB/Parquet no piloto (já é o padrão do repo); TimescaleDB só se escalar.
- **Modelos:** Python (pipeline da seção 2.2).
- **Dashboard:** Next.js. Telas mínimas: (1) consumo agora e hoje por tomada; (2) ranking de ociosidade em R$/mês; (3) alertas de anomalia com explicação; (4) relatório mensal com economia comprovada (Proof); (5) cadastro de tomadas/equipamentos/horário de funcionamento.
- **Otimização (em ordem de risco):** 1. recomendação textual; 2. agendamento sugerido; 3. comando automático com opt-in e fail-safe (nunca em equipamento crítico: geladeira, câmara fria, equipamento médico).

## 4. Modelo de assinatura

Tudo abaixo é hipótese; **nenhum número foi validado**. Os campos marcados `[?]` precisam de cotação/pesquisa antes de qualquer conta.

| Decisão | Opções | Para discutir |
|---|---|---|
| Hardware | (a) cliente compra, (b) comodato incluso na mensalidade, (c) kit de entrada + assinatura | (b) reduz a barreira de entrada mas prende capital em estoque e aumenta o risco de churn |
| Preço | por tomada/mês, por faixa de nº de tomadas, ou por instalação | `[?]` custo do hardware, custo de nuvem por tomada, preço que o cliente aceita pagar |
| Segmento inicial | **PJ** (direção dada pelo professor; ver 1.1). Resta decidir porte: PME de baixa tensão ou empresa de média tensão com tarifa horária. PF só pelo caso de prova contra distribuidora | PME tem conta maior e mais disposição de pagar para reduzir custo, mas a Premise 2 do design de 11/09 já alertou: "ninguém hoje investiga a própria conta" |
| Narrativa de venda | "assinatura se paga com a economia" | Só funciona se a economia medida > mensalidade. Se a economia média for menor que a mensalidade, o produto não fecha, e isso é o primeiro número a medir no piloto |

Pergunta de unit economics que o piloto precisa responder: **economia mensal medida por cliente > mensalidade + custo de servir?** Se não, a assinatura não se sustenta, por melhor que seja o dashboard.

## 5. Riscos e limites (o que um revisor cético vai apontar)

1. **Demanda sem comprador nomeado.** O professor afirma que o mercado pagaria (sinal de especialista, ver 1.1), mas nenhuma empresa nomeada disse que paga. Continua sendo o maior risco aberto.
2. **Cobertura da medição.** Tomada só mede o que se liga nela. As maiores cargas residenciais/PME brasileiras, como chuveiro elétrico e ar-condicionado de maior capacidade, geralmente são ligadas direto no quadro e **ficam fora**. O produto pode medir bem o "barulho" (standby, eletrônicos, geladeira) e perder a maior parte do gasto. Precisa de dado: que fração da conta típica é acessível por tomada?
3. **Economia pode ser pequena.** Desperdício em standby costuma ser fração modesta da conta `[?]`. Se for pouco, a mensalidade não se paga.
4. **Concorrência.** Existem tomadas inteligentes baratas com app próprio no mercado, e plataformas de monitoramento de energia no exterior. A diferenciação tem que estar em diagnóstico/otimização/comprovação, não em ligar e desligar pelo celular. `[?]` levantar concorrentes brasileiros e preços antes de afirmar o diferencial.
5. **Hardware e regulação.** Certificação, segurança elétrica, garantia, logística e suporte. É um problema que o MAPEN, hoje 100% software/dados, não tem.
6. **LGPD.** Consumo por equipamento e horário revela rotina da casa (quando há alguém, quando dorme). Dado pessoal sensível na prática. Já estava como pendência em 11/09; aqui vira requisito de desenho desde o início.
7. **Dado ruim de rede doméstica.** Wi-Fi cai, relógio deriva, tomada reinicia. Qualidade do dado é problema de engenharia primeiro, de modelagem depois.
8. **Dependência de fabricante.** API/nuvem fechada pode mudar ou cobrar. Preferir firmware aberto/MQTT local no piloto.
9. **Gargalo não é código.** Backend, dashboard e modelos o grupo executa rápido. O que limita é hardware (compra, certificação, instalação), empresas-piloto e decisões do grupo.

## 6. Proposta de piloto (mínimo que gera evidência)

1. 5 a 10 casas/PMEs de gente conhecida (nomeadas), com 4 a 8 tomadas cada, por 4 a 8 semanas.
2. Medir: (a) fração do consumo da conta coberta pelas tomadas, (b) ociosidade detectada em R$/mês, (c) quantos alertas o cliente considerou úteis, (d) se agiu em cima deles, (e) economia observada.
3. Pergunta final ao cliente: *pagaria?* e *quanto?* Mesmo critério de sucesso fraco/forte do design de 11/09 (usaria de graça ≠ pagaria).
4. Sem rótulo real não reportamos precisão: reportamos nº de alertas corroborados pelo próprio cliente.

## 7. Perguntas para a Natália decidir

1. **Segmento inicial:** PJ (direção do professor). Qual porte e setor? (afeta preço, tarifa aplicável e tipo de equipamento.)
2. **Hardware:** decidido em 2026-10-01: hardware próprio com energia autônoma é requisito (registro independente de rede e conexão); tomada comercial fica como atalho. Ver plano, seção 6.
3. **Escopo do MVP:** registro com horário + custo por tarifa horária + ranking de equipamentos + desligamento remoto/agendado (núcleo definido pelo professor). Entra ou não a prova de queda/dano já no MVP, ou só como fase 2?
4. **Fase A:** manter como trilha acadêmica separada (recomendação) ou absorver na nova narrativa?
5. **Neoenergia:** canal/parceira (seção 2.3) ou contraparte adversarial (prova de dano, seção 1.1.2)? Não dá para vender as duas coisas ao mesmo tempo.
6. **Quem do grupo cuida de quê:** hardware/firmware, backend/ingestão, modelos, dashboard, regulatório/LGPD, entrevistas de demanda.
7. **Primeira empresa nomeada** para a pergunta "pagaria?". Pedir ao professor 1 a 2 contatos de empresas é o caminho mais curto. Sem nome, o piloto não começa.
8. **Perguntas ao professor:** que tipo de empresa e equipamento ele imagina? Qual a forma de cobrança que ele considera viável (mensalidade fixa, % da economia)?

## 8. Próximos passos propostos (ordem)

1. Natália revisa este documento e responde a seção 7.
2. Levantar 3 a 5 modelos de tomada (preço, corrente, certificação, firmware aberto) e concorrentes diretos no Brasil. Fecha os `[?]` do preço e do diferencial.
3. Nomear 3 pessoas/PMEs candidatas ao piloto.
4. Prototipar a ingestão de 1 tomada → DuckDB → gráfico simples (1 dia de trabalho, serve para medir a qualidade real do dado).
5. Só depois: dashboard e modelos.
