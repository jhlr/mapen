# SPEC (rascunho para confirmação) — Pivô MAPEN: assinatura de sensores IoT + aconselhamento energético PJ

Origem: `docs/plano-pivo-iot-assinatura-2026-10-01.md` (escopo aprovado pela Natália em 2026-10-01). Revisão adversarial por agente sem contexto feita em 2026-10-01; correções dos achados 1, 3, 4, 6, 7, 9, 11, 12, 13 aplicadas aqui. Achados 2 (hardware próprio em cliente) e 5 (gate de demanda) decididos conforme o grupo: ver `docs/plano-pivo-iot-assinatura-2026-10-01.md` seção 6. Estrutura: 1 épico + 5 issues filhas (M0 a M4). Repo `jhlr/mapen` foi tornado **privado** em 2026-10-01 antes de qualquer issue ser aberta.

---

# ÉPICO — Pivô MAPEN: assinatura de sensores IoT + aconselhamento energético PJ

## Context

O MAPEN deixa de ser só detecção de perdas do lado da distribuidora (Fase A, segue como trilha acadêmica separada) e ganha um produto de assinatura mensal para empresas: aconselhamento energético contínuo (horário de uso, preço por faixa horária, equipamentos de maior custo) apoiado por sensores IoT (tomada inteligente, medidor de quadro) que registram consumo com data e hora e permitem desligamento remoto. Um professor da área afirma que há mercado que pagaria; nenhuma empresa nomeada confirmou. O grupo está em pré-incubação, então o épico otimiza para aprender rápido e barato.

## Current State (verificado em 2026-10-01)

| Item | Estado |
|---|---|
| Stack | `pyproject.toml`: pandas, pyarrow, duckdb, openpyxl, matplotlib, huggingface_hub, xgboost, lightgbm, scikit-learn. `shap` ausente. `py-modules = []` (sem pacote Python, só scripts planos em `src/`) |
| `src/` | `ons_load.py`, `plot_br_consumo_rede.py`, `plot_br_consumo.py`, `plot_br_grid.py`, `plot_perdas_ano.py`, `redflags_perdas.py` |
| Dados | `data/consumo/{ons,epe,samp,samp_balanco}`, `data/analise/*.csv`. Todos agregados (distribuidora/UF); nenhum por equipamento |
| Ingestão de sensor, hardware, dashboard | **Não existem** |
| `src/model_redflags.py` | Não existe (Fase A, fora deste épico) |

## Proposed Change

Entregar em marcos, **serviço primeiro, sensor depois**:

```
#M0 Preparação ──> #M1 Serviço sem sensor ──> #M2 Sensor + dashboard ──> #M3 Economia medida ──> #M4 Prova de queda/dano
   │                                              ^                          
   └── compra de componentes (iniciar no M0) ─────┘  (caminho crítico: hardware e dados reais iniciais)
```

Sequência justificada: M1 depende só do M0 (tarifa vigente e licença do dataset) e de dado público; M2 depende de compra de componentes, que deve começar no M0 pelo prazo de entrega; M3 depende de dado real de M2; M4 depende de parecer jurídico, da decisão sobre a Neoenergia e de log confiável de M2.

A validação de mercado vem do especialista (professor) e está aceita como ponto de partida; o que o épico exige agora é **dado real inicial** (ver M0 e M3), não entrevistas.

## Acceptance Criteria (do épico)

1. M0 e M1 fechadas. M2 a M4 fechadas ou com bloqueio externo registrado na issue (qual item, quem é o dono, data do registro).
2. Nenhum número de preço, economia, precisão ou recall aparece em doc ou relatório sem fonte citada ou medição registrada.
3. Todo desligamento remoto executado está registrado em `evento` com ordem, origem e regra.
4. Tests passando em todas as issues que alteram código.

## Out of Scope

Nome comercial, preço de venda final, produção em escala e certificação final do hardware próprio, escrita de artigo novo, Fase A (redflags de perda), integração técnica com a Neoenergia (a posição estratégica, canal ou contraparte, é pré-requisito do M4, ver abaixo), app mobile.

## Decisões sensíveis registradas (de propósito)

1. Desligamento automático só com regra explícita do cliente, nunca em equipamento marcado como crítico.
2. Prova contra distribuidora fica no escopo, mas depois do piloto e do parecer jurídico.
3. Sem precisão/recall estimados: sem rótulo real, o critério é nº de alertas corroborados pelo cliente.
4. **Hardware próprio com energia autônoma** (decisão do grupo, 2026-10-01): o dispositivo tem fonte própria de energia e memória local para registrar horário e oscilações de carga independente de conexão e de rede elétrica. Isso é requisito do produto, não otimização: sem ele, queda de energia e queda de Wi-Fi são indistinguíveis. Tomada comercial entra só como atalho de M1/M2 para o que não depende disso.

---

# ISSUE M0 — Preparação: cotações, tarifa, segmento, unit economics, datasets, regulação, referências, dados reais iniciais

## Context

Todo marco seguinte depende de fatos que hoje estão como `[?]` nos docs: preço e certificação do sensor, tarifa vigente, licença dos datasets, regra de ressarcimento da ANEEL, fonte de dado real inicial. M0 transforma esses `[?]` em fato com fonte, ou em "não encontrado" explícito.

## Current State

`docs/designs/mapen-assinatura-iot-tomadas.md` e `docs/plano-pivo-iot-assinatura-2026-10-01.md` contêm os `[?]`. Nenhuma pasta `docs/hardware/` ou `docs/regulacao/` existe.

## Proposed Change (docs, sem código)

| Arquivo novo | Conteúdo |
|---|---|
| `docs/hardware/candidatos.md` | Tabela com ≥3 modelos de tomada e ≥1 medidor de quadro (pinça de corrente) como **referência e atalho**: preço em R$ com data e link, corrente/tensão máxima, protocolo (MQTT/API local/nuvem), firmware aberto (sim/não), memória local e bateria (sim/não), certificação Anatel/Inmetro (sim/não/não encontrado), link da fonte |
| `docs/hardware/proprio_bom.md` | Viabilidade do hardware próprio com energia autônoma: lista de materiais (microcontrolador com Wi-Fi, CI de medição de energia, relógio RTC, memória flash, supercapacitor ou bateria), custo unitário cotado com link, autonomia mínima N de registro sem rede elétrica (N derivado da menor queda relevante pela regra ANEEL lida neste marco; o valor entra aqui com a fonte), circuito dedicado de detecção de falta de tensão, riscos de segurança elétrica e de bateria (comparar supercapacitor × lítio), caminho de certificação Anatel/Inmetro |
| `docs/regulacao/tarifas_neoenergia_pe.md` | Modalidades (convencional, branca, verde/azul) com faixas horárias e valores vigentes, citando número e data da resolução ANEEL |
| `docs/regulacao/ressarcimento_dano_eletrico.md` | Texto vigente da regra ANEEL (artigos e prazos citados), padrão de evidência exigido, quem tem ônus da prova. Inclui nota LGPD sobre consumo por equipamento |
| `docs/datasets_publicos.md` | Para cada dataset candidato (no mínimo BDG2 e CU-BEMS): URL, licença com texto citado, tamanho, granularidade, adequação ao uso comercial. Decide qual alimenta M1 |
| `docs/referencias.md` | Cada artigo pré-existente indicado pelo grupo: citação, resumo em 3 linhas, o que reaproveitamos |
| `docs/dados_reais_iniciais.md` | De onde vem o primeiro dado real: dataset público escolhido (M1) e ambiente do próprio grupo para o sensor (bancada, casa, laboratório), com período e equipamentos medidos |
| `docs/unit_economics.md` | Modelo de uma página: custo unitário do hardware (do `proprio_bom.md`), nuvem e suporte por sensor/mês, preço-piso para cobrir custo, economia mensal que o cliente precisa ter para a assinatura fazer sentido. Entradas sem fonte ficam `[?]`, nunca estimadas |
| `docs/segmento.md` | Segmento-alvo decidido: média tensão com tarifa horária ou PME de baixa tensão (convencional ou branca), com a fonte de quanto desse segmento tem tarifa diferenciada por horário. Se o segmento escolhido está na convencional, registrar que mudar horário não economiza e o valor vem de outro lado (equipamento, ociosidade, demanda) |
| `docs/regulacao/responsabilidade.md` | Rascunho dos pontos a cobrir em termo de uso: responsabilidade por desligamento remoto, equipamentos críticos, seguro, LGPD |

Dataset de partida proposto (a confirmar neste marco): **CU-BEMS** (consumo por zona, ar-condicionado, iluminação e tomadas num prédio de escritórios em Bangkok, 2018-2019) para ranking por equipamento; **Building Data Genome Project 2** (3.053 medidores em 1.636 prédios não residenciais, 2016-2017, horário) para custo por faixa horária e benchmark de prédio inteiro. Limitação a registrar: ambos são estrangeiros; aplicar tarifa brasileira a curva estrangeira demonstra o método, não o comportamento de carga no Brasil.

## Acceptance Criteria

1. Cada um dos 10 arquivos existe e está commitado.
2. Cada linha de `candidatos.md`, `tarifas_neoenergia_pe.md` e `ressarcimento_dano_eletrico.md` tem URL de fonte; lacunas aparecem como "não encontrado em <data>", nunca em branco.
3. `datasets_publicos.md` cita o texto literal da licença de cada dataset e conclui "uso permitido / não permitido / incerto" para cada um.
4. `dados_reais_iniciais.md` nomeia a fonte de dado real do M1 e o ambiente de coleta do M2, ambos com responsável do grupo.
5. `unit_economics.md` tem a fórmula completa; cada entrada tem fonte ou `[?]`; o doc diz se o serviço só com fatura (M1) já captura a maior parte do valor, ou não.
6. Os `[?]` de preço, certificação e tarifa nos dois docs de design/plano são substituídos por link para o novo arquivo.

## Testing Plan

Revisão manual: abrir 100% dos links de fonte. Sem testes automatizados.

## Rollback

Revert do commit; docs só.

## Effort

Hardware comercial 3h, hardware próprio (BOM e viabilidade) 5h, tarifa 2h, segmento 2h, unit economics 3h, regulação e responsabilidade 5h, datasets 2h, referências 2h, dados reais iniciais 1h. Total ~25h. Pedidos de componentes com prazo longo de entrega saem no M0, em paralelo.

## Files Reference

Ver tabela acima; mais `docs/designs/mapen-assinatura-iot-tomadas.md` e `docs/plano-pivo-iot-assinatura-2026-10-01.md` (troca dos `[?]`).

## Out of Scope

Comprar ou montar hardware; parecer jurídico formal (M4).

---

# ISSUE M1 — Serviço sem sensor: aconselhamento a partir de curva de carga pública

## Context

Prova o núcleo do produto (custo por faixa horária, ranking de equipamentos, recomendação de mover/desligar) sem depender de hardware ou empresa. Entrada: dataset **real público** definido em M0. **É teste de código e demonstração de método, não aconselhamento a cliente**: curva estrangeira com tarifa brasileira não mostra o comportamento de carga no Brasil.

## Current State

Não existe pacote Python de aconselhamento. `src/redflags_perdas.py` tem a lógica de z-score sazonal por unidade que serve de baseline para anomalia; `perda_dist()` é referenciada por design mas a função de anomalia por equipamento não existe.

## Proposed Change

Pacote novo `src/mapen_aconselhamento/` (biblioteca importável, sem script solto), registrado em `pyproject.toml` (`[tool.setuptools.packages.find]` com `where = ["src"]`), `shap` adicionado às dependências.

| Módulo | Responsabilidade |
|---|---|
| `ingest.py` | Carrega o dataset escolhido em M0 para a tabela DuckDB `leitura(sensor_id, equipamento_id, ts, potencia_w, tensao_v, kwh)`; reindexa cada série a calendário completo e marca lacunas como `NULL` com flag `ausente`, sem interpolar |
| `tarifa.py` | Lê a tabela de tarifa de `docs/regulacao/tarifas_neoenergia_pe.md` (convertida em `data/tarifas/neoenergia_pe.csv`) e devolve o preço R$/kWh por timestamp e modalidade |
| `custo.py` | Custo por equipamento e faixa horária |
| `ranking.py` | Top-N equipamentos por custo mensal |
| `recomenda.py` | Para cargas marcadas `flexivel` em `config/equipamentos.yaml`: economia de mover kWh da faixa A para a faixa B = kWh × (preço A − preço B) |
| `relatorio.py` | Gera relatório markdown por prédio/mês com disclaimer "curva estrangeira + tarifa brasileira = demonstração de método" |

## Acceptance Criteria

1. `pip install -e .` instala o pacote e `import mapen_aconselhamento` funciona.
2. Em fixture de 24 h com valores conhecidos, o custo calculado por `custo.py` bate com o cálculo manual dentro de R$ 0,01 nas modalidades convencional e branca.
3. Série com lacuna de ≥2 pontos consecutivos faltando (2 horas ou 2 dias, conforme a granularidade do dataset): o lag/shift não pula a lacuna (teste que falha com `shift()` posicional e passa com a reindexação).
4. Relatório gerado para ≥1 prédio do dataset real, com top-5 equipamentos, custo em R$ e ≥1 recomendação de mover carga flexível com economia calculada.
5. Nenhuma economia é apresentada para carga não marcada `flexivel`.
6. Disclaimer do dataset estrangeiro aparece no relatório.
7. Testes passando.

## Testing Plan

| Camada | O quê | Qtd |
|---|---|---|
| Unit | `tarifa.preco_em(ts)` por modalidade; `custo` na fixture; reindexação com lacuna; `recomenda` só em flexível | +8 |
| Integration | Dataset real (amostra) → DuckDB → relatório | +1 |
| Guard | Teste da lacuna provado vermelho com `git stash` do fix antes de aceitar | +1 |

## Rollback

Revert do PR; sem dado persistente fora de `data/` (gitignored).

## Effort

pacote e ingest 5h, tarifa e custo 4h, ranking e recomendação 3h, relatório 2h, testes 4h. Total ~18h.

## Files Reference

| Arquivo | Mudança |
|---|---|
| `pyproject.toml` | pacote em `src/`, `shap` nas deps |
| `src/mapen_aconselhamento/*.py` | novo |
| `config/equipamentos.yaml` | novo |
| `data/tarifas/neoenergia_pe.csv` | novo, derivado de M0 |
| `tests/test_*.py` | novos |

## Out of Scope

Modelo de ML (M3), sensor (M2), dashboard (M2), previsão de consumo.

---

# ISSUE M2 — Sensor no piloto + ingestão + dashboard + desligamento remoto

## Context

Substitui o dataset público por medição real do cliente e entrega a interface e a ação de desligar.

## Current State

Nenhum código de ingestão de sensor, API ou dashboard.

## Proposed Change

| Componente | Detalhe |
|---|---|
| Hardware próprio (protótipo) | Placa com medição de potência/tensão, RTC, memória flash local e energia autônoma (supercapacitor ou bateria, conforme `proprio_bom.md`). Firmware registra amostras com horário do próprio RTC e as guarda localmente; envia em lote quando a conexão volta. Continua registrando durante falta de energia da rede pelo tempo da autonomia projetada |
| Ingestão | Recebe o lote do dispositivo (MQTT ou HTTP) e grava na mesma tabela `leitura` de M1, usando o timestamp do dispositivo e registrando o desvio vs relógio do servidor. Tomada comercial pode alimentar a mesma tabela como fallback, sem garantia de log em queda |
| Eventos | Tabela `evento(id, ts, tipo, sensor_id, equipamento_id, origem, regra_id, autorizado_por, payload)` para queda, desligamento executado, falha de conexão |
| Segurança do canal de comando | Cada dispositivo tem identidade e chave próprias; todo comando é assinado e carrega nonce e validade curta (rejeita repetição); transporte com TLS; isolamento por cliente; botão físico local que sobrepõe qualquer comando remoto; após reinício o relé volta energizado, salvo regra explícita do equipamento. Primeiro uso real: **só recomendação**, desligamento remoto fica desativado até todos os critérios de segurança abaixo passarem |
| Controle | `regra_desligamento(equipamento_id, cron, ativo, autorizado_por, criado_em)`. Equipamento com `critico = true` rejeita qualquer comando |
| Dashboard | Next.js lendo a base via API (FastAPI). Telas: consumo agora/hoje por sensor, custo por faixa horária, ranking de equipamentos, cadastro de sensor/equipamento/regras, alertas |

## Acceptance Criteria

1. 1 sensor real grava leituras em `leitura` com o mesmo schema do M1.
2. Desconexão induzida de 10 min (Wi-Fi desligado, energia ligada): o dispositivo guarda as amostras localmente e, na volta, 100% do intervalo aparece em `leitura` com horário do dispositivo, e gera 1 `evento` de falha de conexão.
2b. Corte da energia da rede: o dispositivo continua registrando com horário do RTC por **pelo menos N minutos** (N definido no M0 em `proprio_bom.md`, com fonte). Na volta o intervalo aparece em `leitura` e gera 1 `evento` de queda. Se a autonomia medida for menor que N, o critério falha.
3. Comando de relé para equipamento `critico = true` é rejeitado e registrado, 100% das vezes em teste.
4. Comando de desligamento sem `autorizado_por` é rejeitado.
5. Todo desligamento executado gera 1 `evento` com `origem` e `regra_id`.
6. Soak de 24 h com 1 sensor: taxa de amostras recebidas / esperadas ≥ 95%. Se o grupo quiser outro limiar, fixá-lo na issue antes de começar; sem alteração registrada, vale 95%.
6b. **Segurança:** comando com assinatura inválida, nonce repetido ou validade vencida é rejeitado e registrado; botão físico sobrepõe comando remoto; após reinício o relé está energizado; um cliente não consegue comandar sensor de outro (testes automatizados).
6c. **Dados:** retenção e acesso por papel documentados; dado do cliente apagável sob pedido.
7. Dashboard mostra as 5 telas listadas com dados reais do sensor.
8. Testes passando.

## Testing Plan

| Camada | O quê | Qtd |
|---|---|---|
| Unit | rejeição de crítico, rejeição sem autorização, assinatura inválida, nonce repetido, parser do payload, reenvio em lote sem duplicar amostras | +12 |
| Integration | broker MQTT local → ingestão → DuckDB → API | +2 |
| E2E | cadastro de sensor → leitura aparece no dashboard → regra de desligamento executa e gera evento | +1 |
| Bancada | Corte de Wi-Fi e corte de rede elétrica no protótipo, com medição da autonomia | +2 |

## Rollback

Desativar `regra_desligamento` (campo `ativo = false`) e parar o serviço de ingestão. Estado do relé em perda de conexão: **permanece como estava** (não desliga sozinho). Após reinício: energizado.

## Effort

Firmware e protótipo de placa (log local, RTC, energia autônoma, detecção de queda) ~40h, segurança do canal de comando 12h, ingestão 8h, eventos e controle 6h, API 5h, dashboard 12h, testes 10h, instalação e soak 6h. Total ~100h, mais compra de componentes e logística (fora do código). A placa passa a ser o item de maior esforço e risco.

## Dependências

M1 (schema), M0 (autonomia mínima N, modelo de sensor, segurança elétrica e certificação mapeadas). Bloqueio externo: chegada dos componentes.

## Out of Scope

Produção em escala e certificação final da placa, app mobile, multiempresa/multiusuário (piloto é 1 cliente), comando automático sem regra.

---

# ISSUE M3 — Economia medida e modelos de anomalia sobre dados reais

## Context

Transforma leitura em evidência: o aconselhamento reduziu consumo ou custo?

## Current State

Não há modelo por equipamento. A Fase A planeja split walk-forward e teste de vazamento (T2) e checagem de SHAP vs identidade (D7), ainda não implementados.

## Proposed Change

| Módulo | Detalhe |
|---|---|
| `modelos/baseline.py` | Consumo esperado por equipamento/hora (regressão com hora, dia da semana, feriado); resíduo = anomalia. Primeiro corte: z-score sazonal recalibrado; segundo: LightGBM/XGBoost |
| `modelos/validacao.py` | Walk-forward temporal + `test_temporal_split_no_leakage()` |
| `modelos/explica.py` | Alerta de z-score: mostra valor do z, baseline e janela. Alerta de modelo de árvore: SHAP; checagem de que a identidade do equipamento não domina a atribuição (D7) |
| `relatorio_economia.py` | Antes × depois de cada ação aplicada, com baseline normalizado por dia da semana/temperatura quando houver |
| `docs/resultados_dados_reais.md` | Resultado em dado real: o que o aconselhamento recomendou, o que foi aplicado, o que mudou em kWh e R$, e o que não se pôde concluir. A validação de mercado do professor segue como premissa registrada; este doc registra evidência medida, não opinião |

## Acceptance Criteria

1. `test_temporal_split_no_leakage` passa e foi visto **vermelho** (via `git stash` do fix) antes de aceito.
2. Cada alerta traz sua explicação: z-score com baseline e janela (primeiro corte) ou SHAP com as 3 principais features (modelo de árvore).
3. Relatório de economia traz, para cada ação aplicada, kWh e R$ antes/depois. Baseline com menos de 4 semanas completas de histórico é marcada "fraca" (limiar proposto, ajustável na abertura da issue).
4. Zero métrica de precisão/recall reportada sem rótulo real; o relatório mostra nº de alertas corroborados pelo cliente.
5. `resultados_dados_reais.md` existe e usa dado real de sensor (ambiente do grupo, conforme `dados_reais_iniciais.md`), com período e equipamentos medidos, incluindo o que não se pôde concluir.
6. Testes passando.

## Testing Plan

| Camada | O quê | Qtd |
|---|---|---|
| Unit | split sem vazamento; baseline em série sintética com anomalia injetada conhecida; normalização antes×depois | +6 |
| Integration | Leitura do piloto → alertas → relatório | +1 |

## Rollback

Revert do PR; desligar o job de geração de alertas.

## Effort

Baseline 8h, validação e testes 8h, explicação e checagem D7 5h, relatório de economia 6h, análise dos dados reais 4h. Total ~31h.

## Dependências

M2 (≥4 semanas completas de dado real para a baseline deixar de ser "fraca"), M0 (`dados_reais_iniciais.md`).

## Out of Scope

Modelo supervisionado de fraude (sem rótulo), previsão de custo da próxima fatura.

---

# ISSUE M4 — Registro organizado de queda e dano a aparelhos (módulo condicional)

## Context

Permite ao cliente organizar o registro de um evento elétrico para apoiar um pedido de ressarcimento à distribuidora. É **registro organizado de incidente, não prova pericial**: sensor não calibrado e hash do log só mostram que o registro não foi alterado depois. Entra só depois do piloto, do parecer jurídico e da decisão sobre a Neoenergia.

## Current State

`evento` e `leitura` de M2 já guardam tensão e queda com carimbo de tempo do dispositivo. Nada de integridade de log, relatório de evento ou parecer jurídico.

## Proposed Change

| Componente | Detalhe |
|---|---|
| Log íntegro | Blocos de leituras/eventos encadeados por hash; verificação detecta qualquer edição |
| Relógio | Sincronização NTP e desvio do dispositivo registrado por bloco |
| Queda × Wi-Fi caído | Resolvido pelo hardware de M2: o dispositivo tem energia autônoma e RTC, grava a falta de tensão por conta própria e envia ao voltar. Evento de queda só é marcado quando o próprio dispositivo mediu a falta de tensão |
| Relatório de evento | PDF/markdown com linha do tempo, tensão, desvio de relógio e limitações da medição, no formato exigido pela regra de M0 |

## Acceptance Criteria

1. **Gates:** (a) existe `docs/regulacao/parecer_<data>.md` com parecer de pessoa habilitada em regulação do consumidor; (b) existe `docs/decisao_neoenergia.md` com a posição do grupo (canal ou contraparte) e a justificativa. Nenhum merge desta issue antes dos dois.
2. Alterar 1 registro do log faz a verificação de cadeia falhar (teste).
3. Simulação de queda com roteador desligado e tomada com energia: **não** gera evento de queda (teste).
4. Simulação de queda real (energia da tomada cortada): gera evento após a volta, com timestamp do dispositivo.
5. Relatório de evento declara as limitações (sensor não calibrado, indício e não prova pericial).
6. Testes passando.

## Testing Plan

| Camada | O quê | Qtd |
|---|---|---|
| Unit | cadeia de hash, detecção de edição, classificação queda/Wi-Fi | +6 |
| Integration | corte de energia físico → evento → relatório | +1 |

## Rollback

Desativar o módulo por flag; dados de M2 permanecem.

## Effort

Log íntegro 5h, lógica queda/Wi-Fi 6h, relatório 5h, testes 4h. Total ~20h, mais espera do parecer.

## Dependências

M2 concluído, M0 (regra ANEEL lida), parecer jurídico (externo), decisão do grupo sobre a Neoenergia.

## Out of Scope

Peticionar à distribuidora em nome do cliente, calibração metrológica, laudo de dano ao aparelho.

---

## Dependency Graph

```
M0 ──> M1 ──> M2 ──> M3
 │             │
 └─────────────┴──> M4 (gate: parecer jurídico)
```

Rationale: M1 não depende de nada externo; M2 depende de hardware; M3 de dado real e empresa; M4 de log confiável e parecer.

## Related

- `docs/designs/mapen-assinatura-iot-tomadas.md`
- `docs/plano-pivo-iot-assinatura-2026-10-01.md`
- `TODOS.md` (validação de redflags, Fase A, fora do épico)
