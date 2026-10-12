# AV1 • Do projeto ao dashboard: especificações do trabalho

**Data:** 2026-10-12 | **Disciplina:** Análise e Visualização de Dados 2026.2 | **Grupo:** 3 (MAPEN/MAPPEN)

Este documento resume o que o professor pede, sem comparar com o estado do projeto. A comparação está em `docs/av1-analise-comparativa-2026-10-12.md`.

**Fontes (PDFs do professor, publicados em 04/10/2026):** 01-enunciado-AV1, 02-guia-racionalizacao-dashboard, 03-modelo-racionalizacao, 07-instrucoes-detalhadas-por-grupo.

**Pendente de divulgação pelo professor:** peso da AV1 e prazo. Não usar a data de 29/09/2026 da prova anterior.

## 1. Modalidade

1. Trabalho no grupo, avaliado exclusivamente pelos arquivos entregues. Sem apresentação, arguição ou vídeo obrigatório.
2. Nota coletiva de 0 a 10. Contribuição na AV1 = nota × W/10 (W = peso, a definir).
3. Entregar um protótipo de dashboard para uma decisão do próprio projeto, mais a evidência da racionalização usada para construí-lo.
4. Nota pela coerência entre pergunta, dado, cálculo, representação e decisão. Quantidade de funcionalidades, volume de código, uso de IA, hardware ou base maior não dão pontos.

## 2. Etapas obrigatórias

1. Descrever estado atual, usuário, decisão, escopo e três perguntas analíticas (P1 a P3).
2. Inventariar fontes e produzir o dicionário dos campos usados.
3. Preparar o recorte e registrar cinco verificações de qualidade.
4. Explorar os dados e definir medidas com fórmulas, unidades e denominadores.
5. Justificar três visualizações; comparar duas alternativas para pelo menos uma.
6. Compor o dashboard declarando filtros, estados sem dados, fontes e limitações.
7. Conferir um indicador de forma independente, testar dois recortes e um caso sem dados, e fazer um teste de leitura com pessoa externa ao grupo.
8. Entregar o registro visual comentado: rascunho inicial, protótipo anotado, matriz de decisões e justificativa de uma revisão. Registrar contribuições e uso de IA.

## 3. Protótipo mínimo

1. Uma página com três vistas analíticas calculadas (V1 a V3), com título, unidade, fonte, recorte e síntese textual.
2. Cartões de totais complementam, mas não substituem as três vistas.
3. Ao menos uma distribuição, série temporal ou relação que contextualize a comparação principal.
4. Qualquer tecnologia (R/Quarto, Python, BI, app existente).
5. Versão estática é aceita se trouxer dois estados recalculados do painel e a especificação das interações.
6. Só telas desenhadas, sem cálculo demonstrável, não atendem ao mínimo.
7. Fora do mínimo: nuvem, autenticação, app de campo, IoT, previsão, integração automática, controle de equipamentos, publicação pública. Só entram se já existirem e ajudarem nas perguntas.

## 4. Encomenda do Grupo 3 (MAPEN/MAPPEN)

**Foco:** fixar o recorte e explicar consumo observado versus referência.
**Evidência específica:** origem dos dados, linha de base, comparação visual e sensibilidade ao calendário ou à referência.

**Decisão sugerida:** o gestor de uma unidade escolhe onde investigar um desvio de consumo. Pergunta: "Em quais equipamentos ou períodos o consumo ficou acima ou abaixo de uma referência, e o que deve ser investigado?"

### 4.1 Passo 1: entrada (escolher uma)

1. Leituras por equipamento (ativo, intervalo, grandeza, qualidade).
2. Histórico agregado ou fatura, na periodicidade disponível, sem inventar curva horária.
3. Simulação do próprio projeto, com intervalos, cargas, parâmetros e regra de geração declarados.

Se houver dado real, diferenciar medido, derivado e estimado. Não é preciso esperar a compra de tomadas.

### 4.2 Passo 2: campos

| Campo | Finalidade | Regra |
|---|---|---|
| Unidade/ativo e período | Identificar consumo comparável | Declarar chave e duração do intervalo |
| Energia ou potência | Medida de entrada | kWh é energia; kW é potência |
| Horário/estado de operação | Contextualizar o esperado | Carga essencial pode operar fora do expediente |
| Referência esperada | Calcular desvio | Registrar método, janela e origem dos dados |
| Tarifa (se usada) | Estimativa monetária | Declarar unidade e hipótese; não confundir com fatura integral |

### 4.3 Passo 3: preparar e solicitar o que falta

1. Verificar duplicidades, ausências, tipos e unidades, valores plausíveis e cobertura dos intervalos.
2. Acumulado: documentar diferenças entre leituras e reinícios.
3. Energia = potência média × duração em horas; leitura instantânea exige hipótese de integração explícita.
4. Solicitar histórico comparável, calendário operacional e identificação de cargas essenciais.
5. Um total mensal isolado não sustenta linha de base: usar cenário identificado ou obter comparação adicional.

### 4.4 Linha de base (definir antes de desenhar)

1. Regra simples e auditável: mediana de intervalos anteriores comparáveis, ou referência operacional explicitamente estimada.
2. Informar quais dias, turnos ou níveis de produção são comparáveis.
3. A janela histórica não inclui o intervalo avaliado.
4. Sem dado observacional de referência: usar referência hipotética e rotular o resultado como cenário. Não chamar de "consumo normal medido".

### 4.5 Medidas

1. Desvio = observado − esperado (mesma unidade e período).
2. Desvio relativo = 100 × desvio / esperado, só quando esperado > 0. Se esperado = 0, mostrar o desvio absoluto e informar que o relativo não se calcula.
3. Estimativa monetária (opcional) = soma(desvio positivo do intervalo × tarifa do intervalo), declarada como cenário parcial. Não adicionar tarifa horária se ela não se aplica ao contrato. Retorno financeiro não é obrigatório.
4. Ranking: distinguir **saldo de desvios** (positivos e negativos se compensam) de **soma dos desvios positivos**, e usar o nome correspondente ao cálculo.

### 4.6 As três vistas (rota sugerida; pode ser substituída se justificado)

| ID | Pergunta | Visual sugerido | Limite obrigatório |
|---|---|---|---|
| V1 | Quando o consumo se afastou da referência? | Linhas de observado e esperado na mesma unidade; lacunas como ausência, não zero | Referência é estimativa; períodos comparados identificados |
| V2 | Onde investigar primeiro? | Barras horizontais do desvio por ativo ou período, com referência zero, unidade e sinal preservado | Desvio positivo é candidato a investigação, não economia garantida |
| V3 | O padrão acompanha o funcionamento? | Distribuição por estado operacional ou perfil por horário em períodos comparáveis; com dado mensal, distribuição mensal ou relação com produção/ocupação | Sem dado horário, trocar por comparação mensal contextualizada; não criar associação com variável inventada sem rotular simulação |

### 4.7 Organização da página

1. Cabeçalho: unidade, período e fonte.
2. V1 mostra a comparação; V2 orienta a investigação; V3 dá contexto.
3. Regra da linha de base e seus limites visíveis perto do resultado.
4. Estado geral e estado filtrado por ativo/período, mais ausência de dado e referência zero.

### 4.8 Exemplo de conferência do professor

Observado 12 kWh, esperado 10 kWh no mesmo intervalo: desvio +2 kWh, relativo +20%. Com referência revisada para 11 kWh: desvio +1 kWh, cerca de +9,1%. Demonstra dependência da premissa; não comprova economia realizável.

### 4.9 Critério específico de conclusão

1. Mostrar como uma mudança justificada na linha de base ou no calendário altera o ranking.
2. Saber explicar kW versus kWh, a origem da referência e por que não se pode prometer economia só pelo desvio.
3. Controle de tomadas e execução automática ficam fora desta AV1.

### 4.10 Checklist específico do Grupo 3

1. O recorte não mistura a antiga perda de distribuição com a nova pergunta da PME sem justificativa.
2. A referência está documentada e sua origem não é confundida com medição.
3. As medidas respeitam unidade, duração e regra de agregação.
4. O calendário distingue consumo fora do expediente de consumo dispensável.
5. Uma mudança na premissa foi propagada aos cálculos e ao protótipo.
6. A conclusão recomenda investigação sustentada pela evidência, sem prometer economia não medida.

## 5. Entregáveis

| Entregável | Conteúdo mínimo |
|---|---|
| Relatório de racionalização | 8 a 12 páginas de corpo principal; anexos livres. Estado atual, decisão, perguntas, fontes, qualidade, indicadores, justificativas visuais, achados, limitações, próximos passos |
| Base e dicionário | Recorte, origem, classificação real/simulada, grão, chaves, descrição de todos os campos usados. Só dados permitidos para avaliação |
| Código ou transformações | Scripts, notebook ou arquivo de BI; instruções, dependências, entradas e passos para repetir os cálculos |
| Dashboard | Arquivo executável ou relatório analítico; PDF/imagem legível como cópia. Dois recortes recalculados; caso vazio ou denominador zero documentado |
| Fichas visuais | Uma por vista: pergunta, fórmula, marca, canal, escala, alternativa, limitação; antes/depois de uma revisão |
| Evidência da racionalização | Rascunho/wireframe inicial + captura anotada + matriz pergunta → dado/indicador → escolha visual → elemento da tela + alternativa descartada + mudança justificada |
| Validação e autoria | Conferência independente, teste de leitura, sensibilidade, contribuições individuais, declaração de IA |

**Organização sugerida:** `av1-grupo-N-projeto/` com `dados/`, `codigo/`, `dashboard/`, `evidencias/`, `racionalizacao.pdf`, dicionário e LEIA-ME (ordem de reprodução e arquivo que abre o painel). Incluir índice com nome e localização de cada evidência (sugestão do caderno: E1 recorte e fluxo; E2 base de consumo; E3 referência e contas; E4 protótipo; E5 racionalização; E6 validação e autoria). Elementos numerados V1 a V3, com os mesmos IDs na matriz. Link editável só complementa; endereço de nuvem sem acesso não conta. Se a base tiver restrição, entregar amostra anonimizada ou sintética que reproduza o cálculo.

## 6. Critérios de aceite

1. Cada gráfico está associado a uma pergunta P1 a P3 e a uma medida rastreável.
2. O dado exibido pode ser recalculado a partir do pacote entregue.
3. Nulos, zeros, denominadores e filtros são tratados explicitamente.
4. A natureza real, estimada ou simulada do resultado está visível.
5. Uma mudança entre versão inicial e final foi justificada e demonstrada.
6. A leitura do painel conduz a uma ação e informa uma limitação relevante.

## 7. Rubrica (10 pontos)

| Critério | Máx. | Evidência para pontuação integral |
|---|---|---|
| Recorte e decisão | 1,0 | Estado comprovado, usuário e ação definidos; três perguntas viáveis; encomenda do projeto atendida |
| Dados e qualidade | 2,0 | Origem, grão, dicionário, cinco verificações, decisões rastreáveis, reprodução |
| Indicadores e análise | 1,5 | Fórmulas corretas, agregação e denominadores defendidos; achados proporcionais; conta independente |
| Evidência da racionalização visual | 3,0 | Rascunho e protótipo anotado; matriz para as três vistas; alternativa e revisão justificadas |
| Dashboard e comunicação | 1,0 | Hierarquia, contexto, fontes e limitações; recortes coerentes; legibilidade e acessibilidade verificadas |
| Validação e rastreabilidade | 1,5 | Teste de leitura, caso sem dados, sensibilidade, registro das correções, contribuições, declaração de IA |

**Faixas por critério:** 100% tudo presente e correto; 75% uma lacuna pontual que não altera a conclusão; 50% evidência parcial ou problema relevante delimitado; 25% só intenção ou esboço; 0% ausente. Um erro de denominador afeta "Indicadores"; só afeta "Dashboard" se gerar falha própria de comunicação (ex.: título enganoso). Dados sintéticos declarados podem alcançar nota integral se coerentes, reprodutíveis e lidos como cenários.

## 8. Método do Guia (resumo)

1. **Decisão.** Ficha de decisão: "A pessoa que exerce [papel] consulta o painel a cada [frequência] para decidir [ação] em [contexto]". Três perguntas encadeadas sobre o mesmo problema: situação, explicação exploratória, ação. Fronteiras: período, unidade, território, público, exclusões, conclusão que exigiria dado indisponível. Separar material produzido, dado acessível, implementação demonstrável, hipóteses e dependências ("previsto" ≠ "executado com saída verificável").
2. **Dados.** Inventário por fonte (versão, origem, data de obtenção, cobertura, registros lidos, unidade da linha, restrições, campos, limitações). Classificar cada variável: observado, derivado, estimado por regra ou simulado. Declarar o grão e testar a chave. Dicionário: nome original e tratado, significado e tipo, unidade e frequência, nulos e domínio, papel e uso. Base indisponível: pedido de dados (dado, finalidade, responsável, formato, alternativa) e base sintética com regra de geração e identificação em todos os gráficos.
3. **Preparação.** Preservar entrada, tratar por código registrado, dashboard consome versão identificável. Cinco verificações: chaves/duplicidade; ausência/códigos (nulos separados de zeros válidos); tipos/unidades (datas, decimal, kW/kWh, tempo); domínio/plausibilidade (negativos, extremos, ordem temporal); cobertura/junções (períodos sem registro, chaves sem par, perdas na junção). Mostrar os cinco testes mesmo quando o resultado é "nenhuma ocorrência". Contar linhas antes e depois de cada junção. Tabela de limpeza: problema, detecção, quantidade, regra, motivo, consequência.
4. **Indicadores.** Ficha por indicador: nome, pergunta, fórmula, unidade, grão, agregação, campos, filtros, nulos, denominador, comparação, limitação. Percentual de subconjuntos recalculado de numeradores e denominadores, nunca média simples de taxas. Conta independente fora do painel (entradas, conta, esperado, mostrado, diferença); repetir o mesmo código em outro arquivo não vale.
5. **EDA.** Distribuição, extremos, diferenças entre grupos, evolução temporal. Pelo menos uma vista de contexto. Distinguir observação, hipótese e cenário; cada achado com limitação e próxima verificação. Marcar cada pergunta: respondível, com ressalvas ou bloqueada (se bloqueada, trocar por pergunta verificável ou cenário simulado e registrar a troca). Pedido: três achados ou cenários referenciando tabela e gráfico, mais uma hipótese rejeitada ou interpretação corrigida.
6. **Visualização.** Escolher pela tarefa: comparar categorias → barras/pontos ordenados; evolução → linha; distribuição → histograma/boxplot/pontos; relação → dispersão; localizar → mapa com tabela; cenários → barras/pontos/linhas. Ficha por gráfico: ID, pergunta, leitor, ação, tabela e campos, filtro, indicador, agregação, marca, canal, escala, ordem, cor, título, legenda, alternativa descartada, limitação, interação, teste de compreensão. Barras partem de zero; recorte de eixo em linhas deve ser explícito; não somar kW e kWh. Títulos conclusivos só se corresponderem ao dado e ao filtro ativo; cenário inclui "simulado" ou "estimado". Para pelo menos um gráfico, versão inicial e revisada, com problema, mudança e evidência de melhoria.
7. **Composição.** Áreas: cabeçalho, contexto (2 ou 3 indicadores úteis), vista principal, explicação (2 vistas), detalhe (tabela/lista), rodapé (fonte, atualização, regras de cálculo, limitações). Filtros: valores, estado inicial, gráficos afetados, comportamento dos denominadores, como limpar; filtros ativos visíveis; cada filtro representa uma tarefa. Estados: diferenciar "zero", "sem dados", "não calculável" e "carregando"; amostra pequena aparece com sua contagem; limiar de suficiência justificado. Estática: dois estados equivalentes recalculados. Acessibilidade: não depender só de cor (texto, forma, contorno ou padrão); contraste mínimo 4,5:1 em texto normal, 3:1 em texto grande e componentes gráficos essenciais; síntese textual e tabela de valores; teclado, foco visível e rótulos se houver controles; tamanho de texto legível na exportação.
8. **Validação.** Três situações: recorte padrão, segundo recorte, vazio/denominador zero (totais, indicadores, títulos, unidades, avisos). Teste de leitura com pessoa de fora, três tarefas: achar o principal resultado, comparar dois recortes, dizer qual ação investigaria e qual limitação considera relevante; registrar perfil, respostas, dificuldades, tempo aproximado e correção (colega = "revisão por pares", não validação com cliente). Sensibilidade (MAPEN): trocar a janela da linha de base ou revisar o horário operacional e observar o desvio. Declaração de contribuições individuais e uso de IA com verificação.

## 9. Armadilhas que o professor nomeia

1. Apresentar dado sintético como observação.
2. Tratar associação como causalidade.
3. Tratar desvio energético como economia garantida ou "maior desperdício".
4. Chamar referência arbitrária de "consumo normal medido".
5. Misturar kW e kWh, ou inventar curva horária a partir de total mensal.
6. Converter ausência de leitura em zero.
7. Médias simples de taxas com tamanhos distintos.
8. Capturar a tela pronta e chamar de racionalização (precisa mostrar pergunta, dado, cálculo, representação, alternativa e mudança).
9. Antes/depois sem controle de outros fatores.
10. Repetir o mesmo código em outro arquivo e chamar de conferência independente.

## 10. Uso de IA

Permitido na preparação, com declaração de ferramenta, finalidade, saída aproveitada e verificações feitas. Não inserir dados identificáveis ou restritos em serviços externos. Autoria documentada por contribuições, versões, decisões e verificações. Se não houve uso, declarar isso.

## 11. Modelo de racionalização (campos a preencher, do arquivo 03)

1. Identificação e recorte; 1. Estado atual comprovado (o que existe e onde verificar; hipótese/dependência; mudanças em relação ao SR1; versão de escopo adotada).
2. Decisão e perguntas (frase da decisão, tabela P1 a P3 com ação e fonte candidata, período/unidade, o que fica fora, conclusão que ainda não se sustenta).
3. Pedido de dados faltantes (dado, por que, quem fornece, prazo e alternativa).
4. Encomenda específica (trilha adotada, evidência exigida e onde entregue).
5. Inventário e dicionário. 6. Registro de qualidade (cinco verificações, linhas antes/depois das junções, exclusões e vínculo com o original). 7. Ficha de indicador (com conta independente).
8. Ficha de racionalização visual por V1 a V3 (escolhas visuais, alternativa descartada, o que o leitor pode e não pode concluir, o que muda com os filtros, descrição textual). 9. Revisão de pelo menos uma vista.
10. Wireframe do dashboard. 11. Testes numéricos e de interação. 12. Teste de leitura. 13. Acessibilidade.
14. Resultados e limites. 15. Como reproduzir. 16. Contribuições. 17. Declaração de IA e reutilização. 18. Conferência da entrega.
Anexo A a E: ponto de partida; rascunho e protótipo anotado; matriz do raciocínio; alternativa e revisão; conclusão e limites.
