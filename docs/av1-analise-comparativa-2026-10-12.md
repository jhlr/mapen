# AV1: o MAPEN cumpre as orientações do professor?

**Data:** 2026-10-12 | **Referência:** `docs/av1-especificacoes-2026-10-12.md`

**Base da análise:** leitura de `TODOS.md`, `docs/crisp_dm.md`, `docs/status-pivo-iot-2026-10-03.md`, `docs/dashboard_notas.md`, `docs/m3_notas.md` e da listagem do repositório. Não rodei testes nem abri o dashboard nesta análise; os números são os documentados.

## Veredito

Na substância, o projeto está alinhado com a encomenda do Grupo 3. Na entrega, não: o pacote que o professor avalia (relatório, dicionário, fichas, matriz, teste de leitura etc.) não existe no repositório. Como a nota vem só dos arquivos entregues, essa lacuna pesa mais do que o código.

## 1. O que já cumpre

1. **Referência esperada e desvio.** O M3 calcula observado, esperado (naive sazonal de 168 h) e z-score, com janela histórica que exclui o período avaliado (`m3_notas.md`, seção do alerta naive-168).
2. **Honestidade sobre dados.** Alerta é "candidato não corroborado"; economia é "validação de método com redução injetada"; benchmark é rotulado sintético; sem afirmação de causalidade.
3. **Unidades.** M3 em kW por hora, economia em kWh; sem R$ no antes e depois.
4. **Fora do mínimo.** IoT, autenticação e desligamento remoto existem, mas não são exigidos nem penalizados.
5. **Resultados negativos reportados como são.** Nenhum modelo treinado bateu o naive-168; o antes e depois com controle acerta 12 de 19 (contra 7 de 19 sem controle), fora da tolerância em parte dos equipamentos.
6. **Acessibilidade parcial.** O dashboard mede contraste das faixas, usa hachura além de cor nas faixas de ponta e mediu rolagem horizontal em 375, 768 e 1280 px (`dashboard_notas.md`).

## 2. O que falta, por critério da rubrica

| Critério (máx.) | Estado | Lacuna |
|---|---|---|
| Recorte e decisão (1,0) | Parcial | Não há ficha de decisão com a frase "a pessoa que exerce..." nem P1 a P3 numeradas; a versão de escopo vigente não está declarada |
| Dados e qualidade (2,0) | Parcial | Sem dicionário no formato pedido; as cinco verificações (chaves, nulos, tipos/unidades, plausibilidade, junções) não estão consolidadas e rodadas como registro; sem tabela de limpeza |
| Indicadores e análise (1,5) | Parcial | Fórmulas existem no código e nas notas, mas sem ficha por indicador; sem conta independente fora do painel |
| Racionalização visual (3,0) | Ausente | Sem rascunho/wireframe, captura anotada, matriz V1 a V3, alternativa descartada nem revisão justificada |
| Dashboard e comunicação (1,0) | Parcial | O painel tem 11 telas e não uma página com V1 a V3; sem dois recortes recalculados exportados, estado vazio documentado, tabela equivalente e resumo textual verificados |
| Validação e rastreabilidade (1,5) | Ausente | Sem teste de leitura, sem sensibilidade do ranking, sem contribuições individuais, sem declaração de IA |

Faltam também o relatório de 8 a 12 páginas, o LEIA-ME, o índice de evidências e a estrutura `av1-grupo-3-mapen/`.

## 3. Riscos de conteúdo

1. **Versão do recorte.** README, `TODOS.md` e `crisp_dm.md` ainda descrevem perdas de distribuição (redflags EPE/SAMP); o trabalho recente é IoT para PME. O checklist do Grupo 3 exige não misturar sem justificativa. É preciso declarar a versão adotada e a mudança em relação ao SR1.
2. **Feriados.** O prédio do CU-BEMS fica na Tailândia, mas o calendário usa feriados nacionais brasileiros (`m3_notas.md`, limite 8: "feriados só nacionais (lista do M1)"). A referência é afetada, e a sensibilidade ao calendário é exatamente o que o professor pede. Corrigir ou declarar como limitação.
3. **Tarifa.** A tarifa usada é da Neoenergia PE aplicada a um prédio tailandês. Qualquer valor em R$ é estimativa condicionada e precisa ser rotulado como tal.
4. **Vocabulário.** Uma tela "economia" e "economia" nos títulos conflita com "desvio não é economia garantida". Rotular como cenário sintético; alerta como "candidato a investigação".
5. **Real versus sintético por gráfico.** O professor exige a marcação visível em cada visualização, não só no relatório.
6. **Sensibilidade de verdade.** Já existe comparação do baseline antigo com o naive-168 (detecção 84 para 88 de 114; falso alarme 114 para 99 horas), mas não se mostrou se o equipamento ou período priorizado muda. A rubrica pede essa mudança de ranking.
7. **Teste de leitura e contribuições.** Dependem de pessoas; não são gerados por código.
8. **Dados do ambiente do grupo.** Não há dado medido pelo grupo; o dado real é de terceiros, de outro país, sem cliente. Declarar isso no inventário (classificação real, estimada ou simulada por variável).

## 4. Pontos não verificados

1. Se as telas `/horario` e `/alertas` já cobrem V1 a V3 como o professor descreve.
2. Se há tabela equivalente aos gráficos e resumo textual no dashboard.
3. Peso e prazo da AV1, ainda não divulgados.
4. Se `docs/crisp_dm.md` (de 12/08) está defasado em relação ao código.

## 5. Próximos passos (ordem sugerida)

1. Rodar a sensibilidade: calendário tailandês contra brasileiro e baseline naive-168 contra o antigo, medindo se o ranking de equipamentos muda. Define o conteúdo do restante.
2. Montar `av1-grupo-3-mapen/` reaproveitando o que existe: dicionário, cinco verificações rodadas nos dados, fichas V1 a V3 e matriz.
3. Compor uma página única com V1 a V3, dois recortes (dois equipamentos ou duas semanas) e o estado vazio; exportar capturas.
4. Escrever o relatório a partir do modelo de racionalização (arquivo 03).
5. Com as pessoas: teste de leitura com alguém de fora, contribuições individuais, declaração de IA e decisão sobre a versão do recorte.
