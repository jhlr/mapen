# M1: premissas com fonte (horários da Tarifa Branca, fração movível de HVAC, tributos e bandeira)

Data de pesquisa e acesso de todas as fontes: 2026-10-01. Premissas em uso hoje: `src/mapen_aconselhamento/tarifa.py` (ponta 18-20h59, intermediário 16-17h59, 21h fora de ponta, sem feriados) e `config/equipamentos.yaml` (`fracao_movivel: 0.2`, inventada).

## 1. Postos da Tarifa Branca

### Achados
1. Definição ANEEL: ponta é um período diário de 3 horas consecutivas, exceto sábados, domingos e feriados nacionais. Intermediário são horas conjugadas à ponta, antes e depois, só para quem opta pela Tarifa Branca (Grupo B). Fora de ponta é o complemento. A página da ANEEL diz "de 1 a 1,5 hora" antes e depois da ponta (a leitura por busca resumiu como "uma hora antes e uma depois"; o texto exato da REN 1.000/2021 não foi lido, ver abaixo).
2. Quem define: a distribuidora, na revisão tarifária periódica (4 a 5 anos), conforme REN 1.000/2021 e Proret.
3. Fins de semana e feriados nacionais: todas as horas são fora de ponta. A ANEEL cita 11 feriados nacionais. A lista que apareceu na busca sobre a REN 1.000 (art. 2): 1/jan, 21/abr, 1/mai, 7/set, 12/out, 2/nov, 15/nov, 25/dez, mais terça de carnaval, sexta-feira da Paixão e Corpus Christi (8 + 3 = 11). Em 2026 os móveis caem em 17/02 (carnaval), 03/04 (Paixão) e 04/06 (Corpus Christi). Dia 20/nov (Consciência Negra) não aparece na lista; não confirmado se a REN foi atualizada.
4. Neoenergia PE, página atual (sem data visível): ponta 18:00-20:59, intermediário 16:00-17:59, fora de ponta 21:00-15:59; fins de semana e feriados sempre fora de ponta.
5. Neoenergia PE, matéria de 2018 (início da Tarifa Branca, mesmo site): ponta 17:30-20:29, intermediário 16:30-17:29 e 20:30-21:29, fora de ponta 21:30-16:29.
6. CONFLITO entre 4 e 5. A página atual mostra só uma janela intermediária (2 h antes da ponta) e nenhuma depois, o que não bate com a regra ANEEL de intermediário dos dois lados. Pode ser mudança na revisão tarifária (REH 3.451/2025) ou página incompleta. A nota técnica da REH 3.451/2025 (https://www2.aneel.gov.br/cedoc/reh20253451ti.pdf) teria a resposta, mas retornou 403.
7. 21:00 em Pernambuco: pela página atual, é fora de ponta. Pela matéria de 2018 e pela regra ANEEL, a hora após a ponta seria intermediária. Não confirmado em 2026-10-01 qual vale hoje.

### Fontes
- https://www.gov.br/aneel/pt-br/assuntos/tarifas/entenda-a-tarifa/postos-tarifarios (2026-10-01)
- https://www.gov.br/aneel/pt-br/assuntos/tarifas/tarifa-branca (2026-10-01)
- https://www2.aneel.gov.br/cedoc/ren20211000.html (403; só via resumo de busca, texto primário não lido)
- https://www.neoenergia.com/web/pernambuco/sua-casa/composicao-tarifaria (2026-10-01)
- https://www.neoenergia.com/web/pernambuco/w/saiba-mais-sobre-a-tarifa-branca-que-entra-em-vigor-em-1o-de-janeiro (2026-10-01)

### Confiança
Definição ANEEL e feriados: média-alta (página oficial; lista dos 11 só via resumo). Horários exatos de PE: baixa, por causa do conflito.

### Recomendação para o código
- Manter ponta 18-20h59 e intermediário 16-17h59 (página atual da distribuidora, consistente com o doc de tarifas).
- Tornar 21h configurável (`hora_21_intermediaria`, padrão falso) e rodar o ranking nas duas variantes; declarar no relatório que 21h não está confirmada.
- Implementar feriados: sábado, domingo e os 11 feriados nacionais acima (carnaval, Paixão e Corpus Christi calculados a partir da Páscoa, ex.: `dateutil.easter`) como fora de ponta o dia todo. Hoje o código ignora feriados, o que superestima o custo de ponta nesses dias.
- Pedir a nota técnica da REH 3.451/2025 ou confirmar pelo 116 da Neoenergia antes de usar em contrato.

## 2. Fração movível de ar-condicionado (substituir os 20% inventados)

### Achados (todos de fonte secundária ou estrangeira; nenhum estudo brasileiro encontrado)
1. LBNL (Xu, Haves, Piette, Braun, 2006), prédio de escritórios de 80.000 ft2, massa média, EUA: estratégia simples de limite de demanda reduziu a potência dos chillers em 80-100% entre 14h e 17h, sem reclamação de conforto. Aplica-se a chiller central de escritório com inércia térmica, não a splits.
2. Mesma revisão (citando outros autores): simulação com pré-resfriamento reduz pico em 10-35% (Braun 1990) e 10-50% (Andresen e Brandemuehl 1992, uma zona de escritório); ventilação noturna intensa, 43-56% (simulação, Becker e Paciuk 2002); laboratório, 3% (Conniff 1991) e 40-51% da carga de pico deslocada (Morris 1994).
3. Mesma revisão, testes de campo: cerca de 18% da carga deslocada do dia para a noite em escritório (Ruud 1990); 25% de redução de pico em escritório grande em Chicago (Keeney e Braun 1997); até 100% de 14h às 18h30 em prédio de salas de aula na Califórnia (Mahajan 1993). A revisão diz que os resultados de campo são mistos: de alto a modesto ou nulo.
4. ORNL (Winstead et al.), controle por prioridade em simulação de 80 unidades de ar-condicionado e refrigeração em prédios comerciais: redução de pico de 2,5 kW (15%) num caso reportado; o resumo fala em mais de 15% de redução de pico.
5. NREL/Huang, Ye, Wu, Zuo (Energy, v. 221, 2021): o parque comercial dos EUA poderia cortar 40 GW ou subir 46 GW em dia de pico de verão pelo resfriamento; varejo isolado tem mais flexibilidade absoluta e escritório médio, mais em percentual da potência nominal. O percentual não foi extraído (texto completo não lido).
6. Observação: estes números são redução de pico de potência (kW) em janelas de 2-4 h, em clima temperado, com HVAC central. O mapen mede kWh na banda cara de 3 h, em salas com split. A transferência de valores é uma extrapolação.

### Fontes
- https://www.osti.gov/servlets/purl/980751 (LBNL 2006; texto lido, 2026-10-01)
- https://www.osti.gov/servlets/purl/1649333 (ORNL, Winstead et al.; texto lido, 2026-10-01)
- https://www.osti.gov/pages/biblio/1764735 (NREL/Huang et al. 2021; só resumo, 2026-10-01)

### Confiança
Baixa a média. Faixa de campo consistente (18-25%) mas poucos estudos, só EUA, só escritórios e prédios institucionais. Varejo, clima tropical e splits: não encontrado em 2026-10-01.

### Recomendação para o código
- Trocar `fracao_movivel: 0.2` por três cenários: 0.10 (conservador, piso de campo "modesto"), 0.18 (central, Ruud 1990 via LBNL 2006) e 0.25 (otimista, Keeney e Braun 1997 via LBNL 2006). Reportar sempre a economia nos três.
- Comentário no YAML: "faixa 10-25% de estudos de escritório nos EUA; não validada para o Brasil; validar com medição piloto". Não usar 80-100% (cenário de chiller com massa térmica).
- Aplicar a fração só a escritórios/salas com carga térmica deslocável; tomadas e iluminação continuam 0.

## 3. Tributos e bandeira nos preços da Tarifa Branca

### Achados
1. As tarifas homologadas pela ANEEL (R$/kWh, inclusive a Branca) não incluem ICMS, PIS/Pasep, Cofins, contribuição de iluminação pública nem o adicional de bandeira tarifária. Esses itens entram depois, na fatura. A Tarifa Branca não muda os tributos aplicáveis; ICMS e PIS/Cofins incidem normalmente.
2. O doc `tarifas_neoenergia_pe.md` já afirma "sem tributos e sem bandeira" para B3 (tabela da distribuidora, REH 3.583/2026). Consistente com o item 1.
3. A página da Neoenergia não declara se os valores trazem tributos ("tarifa" é a base; "preço" soma tributos).
4. Alíquota de ICMS aplicável ao B3 em Pernambuco e valor da bandeira vigente: não encontrado em 2026-10-01 (não pesquisado em fonte primária).
5. Se o adicional de bandeira é o mesmo R$/kWh em todos os postos da Branca: não encontrado em 2026-10-01.

### Fontes
- https://www.aneel.gov.br/metodologia-distribuicao e resoluções homologatórias (ex.: https://www.celesc.com.br/arquivos/geral/Re-20243374-Celesc-Dis.pdf), via busca, 2026-10-01 (texto primário não aberto)
- https://www.neoenergia.com/web/pernambuco/sua-casa/composicao-tarifaria (2026-10-01)

### Confiança
Média-alta para "tarifas sem tributos e sem bandeira".

### Recomendação para o código
- Rotular o custo atual como "tarifa base, sem tributos nem bandeira" em relatórios e no nome da coluna.
- Para custo de fatura, aplicar fator de gross-up multiplicativo (ICMS e PIS/Cofins "por dentro") como parâmetro de configuração, vazio até a alíquota ser confirmada. Como é multiplicativo, a economia percentual entre postos não muda; só o valor absoluto em reais.
- Bandeira: parâmetro separado, padrão 0, não somar sem confirmar como incide por posto.

## Pendências
1. Texto primário da REN 1.000/2021 (lista de feriados e horas do intermediário): 403, não lido.
2. Horários vigentes de Neoenergia PE (21h; janela intermediária pós-ponta): conflito entre fontes.
3. Estudo de flexibilidade de HVAC no Brasil ou em clima tropical: não encontrado em 2026-10-01.
