# AV1: o pacote do Grupo 3 cumpre as orientações do professor?

**Data:** 2026-10-12 (revisão da análise de 12/10, após o commit `d0b5571` trazer `av1-grupo-3-mapen/`)
**Referência:** `docs/av1-especificacoes-2026-10-12.md`
**Atualização (mesmo dia):** a divergência de reprodução (item 2.1) e as lacunas do LEIA-ME (item 2.2) foram corrigidas nesta mesma branch; as seções 2, 3 e 5 refletem isso.
**Objeto:** `av1-grupo-3-mapen/` (relatório `racionalizacao.md` e `.pdf`, `dados/`, `codigo/`, `dashboard/`, `evidencias/`, `LEIA-ME.md`).

**O que foi feito nesta conferência:** leitura completa de `racionalizacao.md` e `LEIA-ME.md`; reprodução numa cópia temporária (Python 3.13, pandas 3.0.6, numpy, pytest, Node 22) de `av1_desvio.py`, `conta_independente.py`, `pytest` e `conferencia_cruzada.js`. **Não** abri o painel no navegador nem conferi as imagens de `evidencias/`; não li o código do painel nem `dicionario.md` linha a linha.

## Veredito

O pacote cobre quase tudo que o professor pede e responde à encomenda do Grupo 3. Restam quatro coisas: duas pendências que dependem de pessoas (teste de leitura e contribuições) e dois pontos de consistência a conferir (identificador da fonte e escolha dos 8 ativos). A divergência de reprodução que achei foi corrigida. A nota ainda não é a máxima por causa das pendências, não por falta de método.

## 1. Conferência contra a encomenda do Grupo 3

| Exigência do professor | Onde está no pacote | Situação |
|---|---|---|
| Decisão, usuário, ação, P1 a P3 | Seção 2 | Cumpre. Frase da decisão completa, três perguntas encadeadas |
| Versão do recorte declarada, sem misturar perdas de distribuição | Seção 1 | Cumpre. Usa só a pergunta da PME e explica a mudança |
| Entrada escolhida (histórico, IoT ou simulação) | Seção 1 | Cumpre. Histórico real público (CU-BEMS), rotulado como não sendo do cliente |
| Campos mínimos (ativo, intervalo, energia/potência, horário operacional, referência, qualidade) | Seção 5 e `dicionario.md` | Cumpre. Expediente declarado como hipótese inferida |
| Linha de base auditável, sem o intervalo avaliado | Seção 7 | Cumpre. Mediana do mesmo dia da semana, janela anterior; variantes A, B e C |
| Desvio e desvio relativo só com esperado > 0 | Seção 7 (I1) e caso `z4_Plug` | Cumpre |
| Saldo separado de soma dos positivos | Seção 7 (I2) e revisão 1 | Cumpre. A revisão corrige um erro real de ranking por saldo |
| V1, V2 e V3 com perguntas, escalas e limites | Seção 8 | Cumpre. As três vistas seguem a rota sugerida |
| Alternativa descartada e revisão justificada | Seções 8, 9 e Anexo A | Cumpre. Duas revisões com imagem antes e depois |
| Cinco verificações de qualidade | Seção 6 e `verificacoes_qualidade.json` | Cumpre. Resultado "0 ocorrências" também mostrado |
| Conta independente | Seção 7 | Cumpre. Reproduzi (ver 2) |
| Dois recortes e caso sem dados | Seção 11 e `e4_*.png` | Cumpre no texto; não conferi as imagens |
| Sensibilidade que mude a hipótese relevante | Seção 11 | Cumpre. A prioridade semanal muda nas semanas 2 e 4 com a referência C; a mensal não muda. Relatado com honestidade |
| Segunda premissa (horário operacional) | Seção 11 | Cumpre. Muda a magnitude, não a ordem |
| kW versus kWh, origem da referência, sem promessa de economia | Seções 2, 8 e 14 | Cumpre |
| Declaração de IA com verificações | Seção 17 | Cumpre. Declara Claude Code, finalidade, verificações e o que não foi verificado |
| Teste de leitura com pessoa externa | Seção 12 | **Pendente.** Só há o roteiro |
| Contribuições individuais | Seção 16 | **Pendente.** 6 de 7 integrantes sem preenchimento |

**Mudanças em relação à análise anterior:** os riscos que eu havia apontado (calendário brasileiro num prédio tailandês, "economia" nos títulos, real versus sintético por gráfico, sensibilidade de ranking, consolidação do dicionário e das cinco verificações) foram tratados no pacote. A tarifa fica fora do escopo e o selo "dado real público · referência estimada · desvio ≠ desperdício" aparece no cabeçalho do painel.

## 2. Reprodução (executei numa cópia)

| Passo | Resultado |
|---|---|
| `python codigo/av1_desvio.py` | Rodou. As bases `dados/*.csv` e `dashboard/dados.js` saíram idênticas às do repositório |
| `python codigo/conta_independente.py z1_AC1 2018-11-12 A` | Observado 289,4012, esperado 284,0763, desvio +5,3248 kWh; diferença 0,00003 kWh. Bate com a seção 7 |
| `python -m pytest codigo -q` | 4 passaram |
| `node codigo/conferencia_cruzada.js` (arquivos do repositório) | 2.016 comparações, 0 falhas. Bate com o relatório |
| `node codigo/conferencia_cruzada.js` **depois** de regenerar, antes da correção | 2.016 comparações, **4 falhas** (ver 2.1) |
| Mesma sequência **depois** da correção, em Python 3.11, 3.12 e 3.13 (pandas 3.0.6) | Bases e `resultados_python.json` idênticos aos versionados; conta +5,3248 kWh; 5 testes passam; conferência com **0 falhas** |

### 2.1 Divergência de reprodução (achado e corrigido)

Depois de rodar `av1_desvio.py`, a conferência cruzada falhava em 4 comparações. O que mudava era `evidencias/resultados_python.json`: ativos empatados no ranking (soma dos positivos = 0,0) saíam em ordem diferente.

Causa: `ranking()` ordenava só por `soma_positivos`, sem critério de desempate. O painel (`dashboard/calculo.js`) desempata por nome do ativo. Com 8 ativos e 4 empatados em zero, o pandas 3.0.x devolvia `z1_Plug` antes de `z1_Light`, e a conferência cruzada compara posição por posição.

Correção (nesta branch): `ranking()` ordena por `["soma_positivos", "ativo"]` com `ascending=[False, True]`. Teste novo `test_ranking_desempata_por_nome_do_ativo`, escrito antes da correção: 1 falha sem ela (4 passaram), 5 passam com ela. Regenerar o pacote não altera nenhum arquivo versionado, então nenhum número do relatório muda.

### 2.2 Documentação de como rodar (corrigida)

O LEIA-ME tinha o essencial (arquivo que abre o painel, ordem dos comandos, origem do dado), mas faltavam: instrução de instalação e `requirements.txt`, saída esperada de cada passo, fallback do painel (`python -m http.server`), origem do CSV usado por `--fonte` e o aviso de que ele sobrescreve arquivos. O requisito "Python 3.14" também era mais rígido que o necessário.

Agora o LEIA-ME traz tudo isso, e o requisito virou "Python 3.11 ou mais novo" (testado em 3.11, 3.12 e 3.13; Node 22). A seção 15 do relatório ainda cita Python 3.14, pandas 3.0.5 e Node 26 como ambiente do autor; não foi alterada.

## 3. O que falta, por critério da rubrica

Faixas são minha estimativa, não nota. Usam a escala do professor (100%, 75%, 50%, 25%, 0%).

| Critério (máx.) | Leitura provável | Motivo |
|---|---|---|
| Recorte e decisão (1,0) | Integral | Estado, usuário, ação, P1 a P3 e encomenda atendidos. Conferir seções 1 e 14 contra o SR1 (ver item 4.3) |
| Dados e qualidade (2,0) | Integral ou 75% | Falta só a consistência da fonte (4.2); reprodução e LEIA-ME foram corrigidos (2.1 e 2.2) |
| Indicadores e análise (1,5) | Integral | Fórmulas, denominadores, conta independente e conferência cruzada presentes |
| Racionalização visual (3,0) | 75% a integral | O rascunho foi **reconstruído depois da versão 1**, e o próprio relatório avisa. Pode ser lido como "rascunho inicial parcial". Substituir por um rascunho real, se existir |
| Dashboard e comunicação (1,0) | Integral ou 75% | Acessibilidade calculada mas não auditada por ferramenta (declarado) |
| Validação e rastreabilidade (1,5) | **50% ou menos hoje** | Teste de leitura e 6 de 7 contribuições pendentes |

## 4. Pendências e pontos a decidir

### 4.1 Teste de leitura (seção 12)
Depende de uma pessoa externa. O roteiro está pronto. Registrar perfil (usuário real ou colega), resposta, dificuldade e correção feita; se for colega, classificar como revisão por pares. Não fabricar o teste.

### 4.2 Fonte do dado
A seção 5 cita "figshare 21350166" e o LEIA-ME e a seção 15 citam o DOI `10.6084/m9.figshare.11726517`. São identificadores diferentes. Conferir qual é o do artigo e corrigir o outro.

### 4.3 Seções 1 e 14 contra o SR1
O próprio relatório avisa que o relatório SR1 Innovation e a apresentação MAPPEN não estavam disponíveis para quem redigiu. A Nathália precisa conferir.

### 4.4 Contribuições individuais (seção 16)
Só João Rietra está preenchido, e a revisão dele por colegas também consta como pendente. Cada integrante deve preencher a própria linha com base em trabalho real.

### 4.5 Escolha dos 8 ativos
O M3 trabalha com 24 equipamentos (19 modelados); o painel usa 8. O relatório diz quais são, mas na seção 2 não vi o critério da escolha. Se estiver no dicionário, referenciar; se não, uma frase basta.

### 4.6 Relação com o M3
O painel da AV1 usa mediana do mesmo dia da semana; o M3 usa naive de 168 h e LightGBM. O relatório diz que o código M1 a M3 é "apenas contexto, não reaproveitado". Vale uma frase explicando por que a referência é diferente (a encomenda sugere mediana de intervalos comparáveis), para o avaliador não ler como inconsistência.

### 4.7 Documentos do repositório fora de sincronia
`docs/m3_notas.md` ainda traz na primeira tabela de alertas "160 de z-score e 54 de LightGBM" (214), enquanto o relatório e o status de 03/10 usam 128 e 54 (182) após o naive-168. `docs/crisp_dm.md` (12/08) ainda lista fases como não iniciadas. Não afeta a nota da AV1, mas o relatório cita `m3_notas.md` como fonte.

### 4.8 Limites já declarados no relatório (manter)
Auditoria automática de acessibilidade (axe), leitor de tela real, simulação de daltonismo e calendário de feriados conferido contra fonte oficial. Botões "?" com 28 px, abaixo dos 44 px dos demais controles. Relatório em PDF com 14 páginas; a referência é 8 a 12 de corpo principal, com anexos livres, então basta indicar onde termina o corpo.

## 5. Próximos passos

1. Conferir o identificador da fonte (4.2) e a escolha dos 8 ativos (4.5).
2. Aplicar o teste de leitura com alguém de fora e preencher a seção 12 (4.1).
3. Cada integrante preencher a própria linha da seção 16 (4.4); a Nathália conferir as seções 1 e 14 (4.3).
4. Se existir um rascunho feito antes do painel (papel ou Figma), substituir o reconstruído.
5. Se a seção 15 do relatório for alinhada ao LEIA-ME (Python 3.11 ou mais novo), regenerar `racionalizacao.pdf` e conferir o índice da seção 18.
