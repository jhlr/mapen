# M3 notas de implementacao (2026-10-01)

Pacote `src/mapen_modelos/` (baseline sazonal, LightGBM por equipamento, alertas explicados, benchmark sintetico, antes x depois). Todos os numeros abaixo vem de execucoes reais desta sessao (`python -m mapen_modelos.interface.cli`, relatorio completo em `data/m3/relatorio_m3.md`, gitignored).

## Mapa de camadas (arquivo -> camada)

Mesmas quatro camadas de `mapen_aconselhamento` (interface > infrastructure > application > domain, dependencias so para dentro).

| Arquivo | Camada | Dono de |
|---|---|---|
| `domain/features.py` | domain | features por serie no calendario horario completo; reusa `adicionar_lags`, `reindexar` e `feriados_nacionais` do M1 |
| `domain/baseline.py` | domain | baseline sazonal por hora da semana (feriado = domingo), z-score, semanas completas e flag "fraca" |
| `domain/validacao.py` | domain | dobras walk-forward expansivas e `verificar_sem_vazamento` |
| `domain/anomalia.py` | domain | decisao de anomalia (`abs(z) >= limiar`) |
| `domain/comparacao.py` | domain | antes x depois com baseline normalizado; reducao sintetica |
| `domain/explica.py` | domain | top 3 features SHAP e checagem D7 |
| `domain/injecao.py` | domain | anomalias sinteticas (pico, elevacao fora de horario, ligado continuo) e zona contaminada |
| `application/portas.py` | application | portas `LeitorSeries`, `TreinadorModelo`, `Regressor`, `Explicador` |
| `application/treinar_e_avaliar.py` | application | `TreinarEAvaliar`: walk-forward, MAE baseline x LightGBM, modelos finais |
| `application/detectar_anomalias.py` | application | `DetectarAnomalias`: alertas z-score e LightGBM com explicacao e D7 |
| `application/comparar_antes_depois.py` | application | `CompararAntesDepois`: economia normalizada, reducao sintetica e varredura |
| `application/benchmark_sintetico.py` | application | `BenchmarkSintetico`: injecao, taxa de deteccao e de falso alarme |
| `application/executar_m3.py` | application | `ExecutarM3`: dono do ciclo completo, incluindo `resumir()` (resumo para o dashboard) |
| `application/resumo_m3.py` | application | valor `ResumoM3` (dados, MAE, SHAP/D7, benchmark, baseline fraca) e `montar_resumo`; sem I/O, sem arredondar |
| `infrastructure/serie_duckdb.py` | infrastructure | leitor de series horarias sobre a tabela `leitura` do M1 |
| `infrastructure/subconjunto.py` | infrastructure | carga do subconjunto com o carregador do M1 (`carregar_cu_bems`) |
| `infrastructure/lightgbm_modelo.py` | infrastructure | regressor LightGBM por equipamento |
| `infrastructure/shap_explicador.py` | infrastructure | valores SHAP (ver "Limites" sobre o pacote `shap`) |
| `infrastructure/arquivos.py` | infrastructure | gravacao de relatorio e JSON |
| `interface/relatorio_markdown.py`, `interface/artefatos_json.py`, `interface/cli.py` | interface | relatorio, esquemas JSON (arredondamento de apresentacao) e CLI; `cli.publicar` grava relatorio + `resumo.json`, `alertas.json`, `economia.json` |

Contratos import-linter (`pyproject.toml`, agora com 3 pacotes): camadas do M3; domain/application do M3 sem `duckdb`, `lightgbm`, `shap`, `yaml`, `httpx`, `fastapi`, `starlette`, `mapen_plataforma` nem a infraestrutura/interface do M1; M3 nao depende da plataforma; M1 e M2 nao dependem do M3. Repo real: `Contracts: 9 kept, 0 broken.`

## Dados (subconjunto)

CU-BEMS real, `2018Floor2.csv` (sensor `cu_bems_2018Floor2`), carregado pelo `carregar_cu_bems` do M1 em `data/m3/serie.duckdb` (29 MB, reaproveitado entre execucoes).

- Periodo: 2018-07-01 a 2018-12-02 (exclusivo), 22 semanas exatas (comeca no domingo), 5.322.240 linhas de minuto (24 equipamentos x 221.760 min).
- Treino e walk-forward: 2018-07-01 a 2018-11-04, 3.024 horas (18 semanas). Reservado (alertas, benchmark, antes x depois): 2018-11-04 a 2018-12-02 (4 semanas).
- Hora vale so com os 60 minutos; senao NaN. Horas validas por equipamento no treino: 2.985 a 3.013 de 3.024.
- 24 equipamentos no andar, 19 modelados. Fora (media de treino < 0.05 kW): z2_AC11, z2_AC12, z2_AC13, z2_AC14, z4_Plug.
- Walk-forward: treino inicial 8 semanas, teste de 2 semanas, 5 dobras (testes de 2018-08-26 a 2018-11-04).

## Resultados (reais)

### MAE em dobras de teste (kW, 31.763 horas-equipamento)

| Modelo | MAE agregado (ponderado por horas) |
|---|---|
| Baseline sazonal (hora da semana) | 0.6113 |
| LightGBM por equipamento | 0.2051 |

LightGBM menor em 19 de 19 equipamentos; melhora relativa mediana por equipamento 67.6% (minima 19.3% em z3_Plug). Ressalva: o LightGBM usa lag 1 h, entao e um nowcast de 1 passo; o baseline nao usa nada recente. Ganho grande e esperado, nao prova que o modelo "entende" mais.

### D7: SHAP calendario x historico (periodo reservado, 12.727 horas-equipamento)

Calendario (hora 11.5%, dia da semana 3.3%, feriado 0.1%) = **14.9%** do |SHAP| total; lag/janela movel = **85.1%** (`kw_lag1` 59.5%, `kw_lag168` 13.3%, `kw_lag24` 7.9%, `kw_media24` 2.5%, `kw_desvio24` 1.9%). **O aviso de feature dominante dispara**: `kw_lag1` passa de 50% no agregado e em 11 de 19 equipamentos individualmente (z2_AC5 dispara em `kw_lag24`). Identidade de calendario nao domina (14.9%); a dominancia e do lag 1, coerente com o item acima.

### Alertas em dado real: candidatos, nao corroborados

Periodo reservado, limiar |z| >= 4.0: 160 alertas de z-score e 54 de LightGBM (214 no total), sobre 12.727 horas-equipamento. Zero corroborados pelo cliente (nao ha cliente). Os maiores z-scores sao quedas abaixo do esperado em z2_AC2/AC3/AC4 de manha (ex.: 2018-11-05 09:00; varios em 2018-11-17, um sabado), compativeis com ar-condicionado desligado, nao com falha; nao confirmado.

### Benchmark SINTETICO (nao e precisao/recall em dado real)

Semente 20181104, 2 eventos de cada tipo por equipamento (19), 114 eventos injetados no periodo reservado.

| Detector | Pico | Elevacao fora de horario | Ligado continuo | Total | Falso alarme (horas fora da zona de contaminacao) |
|---|---|---|---|---|---|
| z-score sazonal | 38/38 (100%) | 19/38 (50.0%) | 27/38 (71.1%) | 84/114 (73.7%) | 114/9145 (1.2%) |
| LightGBM (residuo) | 38/38 (100%) | 22/38 (57.9%) | 30/38 (78.9%) | 90/114 (78.9%) | 45/9145 (0.5%) |

O falso alarme sai de serie base real, entao inclui anomalias reais nao rotuladas: e limite superior. A elevacao de 0.5 x P95 e fraca para equipamentos de carga noturna variavel.

### Antes x depois: validacao do METODO (nao e economia real)

Reducao sintetica de 15% em `z1_Light` a partir de 2018-11-18, antes = 2018-11-04 a 2018-11-18, depois = 2018-11-18 a 2018-12-02. A escolha de `z1_Light` foi feita antes de ver qualquer resultado. Tolerancia declarada de antemao: +-3.0 pp.

- **Recuperado: 27.18%. FORA da tolerancia.** Sem a reducao, o mesmo equipamento ja mostrava 14.33% de "economia" (deriva real de nivel).
- Varredura com a mesma reducao em cada um dos 19 equipamentos, um por vez: 7 de 19 dentro de +-3 pp; erro absoluto mediano 6.71 pp; maximo 18.90 pp.
- Controle sem reducao: economia espuria |media| 7.56%, maxima 22.24% (z2_Plug).
- Causa: a carga real tem deriva semanal de 15% a 30% (ocupacao, calendario letivo; razao observado/esperado semanal de z1_Light vai de 0.67 a 1.31), e o baseline sazonal por hora da semana mais um fator de nivel de 2 semanas nao a normaliza. O metodo atual so recupera uma reducao pequena quando o periodo e estavel; nao esta validado em dado real com deriva. O teste de integracao sintetico (sem deriva) recupera 15% dentro de 3 pp.
- Nenhuma baseline fraca: 18 semanas completas de treino. Baseline fraca (menos de 4 semanas com >= 90% das horas validas) e marcada e propagada ao alerta e ao antes x depois; coberta por teste.

## Prova vermelha do guard de vazamento (sem git)

`tests/m3/domain/test_m3_validacao.py::test_temporal_split_no_leakage` usa o splitter real (`SPLITTER = _split_walk_forward`). A referencia ingenua e `_split_aleatorio_ingenuo` (embaralha horas e fatia 75/25); `test_referencia_aleatoria_vaza` afirma que ela vaza. Prova: copia do modulo em `/private/tmp/.../scratchpad/red/` com `SPLITTER = _split_aleatorio_ingenuo`:

```
FAILED test_red_validacao.py::test_temporal_split_no_leakage
E   AssertionError: treino alcanca o periodo de teste
E   assert Timestamp('2026-04-12 23:00:00') < Timestamp('2026-01-05 00:00:00')
1 failed, 4 deselected
```

1 caso falhou (o guard); com o splitter real, passa. Guard a nivel de modelo: `test_metricas_da_dobra_zero_nao_dependem_do_futuro` (adulterar dados depois da dobra 0 nao muda as metricas dela, muda as da dobra 2). Nao foi visto vermelho contra uma implementacao quebrada do `TreinarEAvaliar` (so o guard do splitter foi provado).

Prova vermelha do import-linter (copia de `src/` e `pyproject.toml` em `/private/tmp/.../mapen_red`, fora do repo, sem git, com `domain/ruim_io.py` importando `lightgbm` e `mapen_aconselhamento.infrastructure`, e `application/ruim_camada.py` importando `mapen_modelos.interface`): contratos "M3 camadas" e "M3 dominio e aplicacao sem I/O..." BROKEN, apontando os tres imports.

## Esquemas JSON (para o dashboard; gitignored em `data/m3/`)

`resumo.json` e gerado pelo proprio pipeline (`ExecutarM3.resumir` -> `interface.artefatos_json.montar_resumo_json` -> `cli.publicar`); antes era um script descartavel que lia o markdown e uma nova execucao do CLI nao o atualizava. Esquema em `docs/m2_seguranca_notas.md` ("Contrato M3"), validado pelo adaptador da API. MAE com 4 casas e percentuais com 1 casa, como no relatorio. Reexecucao do CLI em 2026-10-01 (cerca de 2 min): `resumo.json`, `alertas.json`, `economia.json` e `relatorio_m3.md` sairam byte a byte iguais aos anteriores (MAE 0.6113 baseline x 0.2051 LightGBM; 7 de 19 equipamentos dentro da tolerancia).

`alertas.json`: `{versao_esquema, sensor_id, periodo{inicio,fim}, limiar_z, aviso, alertas[]}`; cada alerta: `equipamento` (str), `timestamp` (ISO, ingenuo), `tipo` (`zscore` | `lightgbm`), `esperado_kw`, `observado_kw`, `z` (float; no LightGBM e o residuo / desvio fora da amostra das dobras), `janela_baseline{inicio,fim}` (janela de treino), `top_shap` (null no z-score; no LightGBM lista de 3 `{feature, shap}`), `baseline_fraca` (bool), `status` (sempre `candidato_nao_corroborado`).

`economia.json`: `{versao_esquema, sensor_id, natureza: "validacao_de_metodo_sintetica", aviso, periodo_antes, periodo_depois, reducao_sintetica{equipamento, fracao_pct, a_partir_de}, recuperado_pct, tolerancia_pp, dentro_da_tolerancia, equipamentos[]}`; cada equipamento: `equipamento`, `kwh_antes`, `kwh_depois`, `kwh_contrafactual`, `economia_kwh`, `economia_pct` (com a reducao no equipamento alvo), `economia_pct_sem_reducao` (controle), `recuperado_pct_com_reducao_sintetica` (varredura), `reducao_sintetica_aplicada` (bool), `baseline_fraca` (bool). Valores NaN viram null. Nao ha R$: so kWh.

## Testes

`tests/m3/` (43 testes): unitarios por peca de dominio, guard de vazamento, teste de lacuna (lags e janela NaN no ponto certo; treino nunca recebe alvo NaN), integracao sintetica de semente fixa (benchmark e antes x depois), leitor DuckDB e explicador. Suite completa `gtimeout 900 .venv/bin/pytest -W error -q`: ver o fim da secao "Prova de vermelho da API" para a contagem atual. mypy strict (`src/mapen_modelos`, `tests/m3`, e os demais): `Success: no issues found in 95 source files`.

## Limites e o que NAO esta validado

1. Sem rotulo: nenhuma precisao/recall em dado real. Taxas de deteccao e falso alarme valem so para as anomalias injetadas (tipos, magnitudes e semente deste benchmark).
2. Economia: nao ha intervencao real. O metodo falhou a tolerancia em dado real com deriva (27.18% recuperado para 15% injetado). Melhorias candidatas, nao feitas: covariaveis de temperatura/ocupacao (CU-BEMS tem temperatura, o carregador do M1 ignora), grupo de controle concorrente, janelas mais longas. Normalizacao por temperatura nao implementada.
3. R$ nao calculado no antes x depois (so kWh).
4. D7: o lag 1 domina o SHAP; o LightGBM e um nowcast. Um alerta de LightGBM tem pouca sensibilidade a anomalias persistentes porque o lag 1 as absorve apos a primeira hora.
5. `shap` nao e importado: o pacote 0.52 emite `PendingDeprecationWarning` (matplotlib) na importacao, o que quebra `-W error`, e o aviso e de codigo de terceiros. O adaptador usa a contribuicao TreeSHAP nativa do LightGBM (`pred_contrib=True`), que e o mesmo algoritmo; conferido contra `shap.TreeExplainer` com diferenca maxima 0.0 em valores e valor base. `shap` continua em `pyproject.toml`. `lightgbm` e `shap` ja estavam listados; nenhuma dependencia nova.
6. Limiar |z| >= 4 e hiperparametros do LightGBM fixos, nao ajustados em dado rotulado. Sigma do LightGBM vem do desvio dos residuos fora da amostra das dobras.
7. Um unico andar e 22 semanas de 2018; so predio universitario tropical. Nao generaliza para o piloto.
8. Timestamps ingenuos; feriados so nacionais (lista do M1). Dias letivos/ferias nao entram.

## Contrato CLI -> API do `resumo.json` (teste de fronteira)

`tests/contratos/test_contrato_m3_resumo.py` roda o ciclo real do M3 numa serie sintetica de semente fixa, grava os artefatos por `cli.publicar` (o mesmo caminho do CLI) e le tudo com `ResultadosM3Json`, o adaptador estrito da plataforma. Fica em `tests/contratos` porque cruza dois pacotes; so os testes importam os dois lados (import-linter continua em 9 contratos mantidos, M3 nao depende da plataforma).

Prova de vermelho (sem git): copia de `src/`, `tests/` e `pyproject.toml` em `/private/tmp/m3red1` com a linha que grava `resumo.json` removida de `cli.publicar` (comportamento antigo). Resultado: `2 failed` (`ResultadosM3Indisponiveis: artefato resumo.json ausente`). No repo: `2 passed`.

## Prova de vermelho da API

Os testes de `tests/m2/test_resultados_m3.py` nunca tinham sido vistos vermelhos. Metodo: para cada grupo de comportamento, uma copia de `src/`, `tests/`, `data/tarifas`, `config` e `pyproject.toml` em `/private/tmp/m3red2/NN` recebe UMA mutacao no codigo de producao (o repo nao foi tocado, sem git stash) e roda o arquivo de testes com `PYTHONPATH` apontando para a copia. Copia sem mutacao: todos passam. O teste da copia dos artefatos reais (`test_artefatos_reais_...`) foi excluido (le `data/m3` por caminho relativo ao repo). Script: nao versionado (scratchpad da sessao).

A primeira rodada achou lacunas (mutantes sobreviventes); foram acrescentados 5 testes (7 casos) e a rodada repetida. Resumo final por grupo (primeiro teste vermelho de cada mutacao):

| Grupo | Mutacao (copia) | Resultado |
|---|---|---|
| 401 | `principal_empresa` devolve a empresa A quando a chave nao confere | VERMELHO: `test_sem_chave_ou_chave_errada_e_401` |
| tenant | outra empresa le alertas da dona | VERMELHO: `test_outra_empresa_nao_ve_503_mesmo_sem_artefato`, `test_outra_empresa_recebe_vazio_nunca_o_dado_da_dona` |
| tenant | outra empresa le a economia da dona | VERMELHO: `test_vazio_da_outra_empresa_por_rota` |
| tenant | outra empresa recebe 503 em vez de vazio | VERMELHO: `test_outra_empresa_nao_ve_503_mesmo_sem_artefato` |
| schema | `extra="ignore"` | VERMELHO: `test_artefato_fora_do_esquema_e_503[...campo_extra]` |
| schema | `versao_esquema: int` | VERMELHO: `...[_quebrar_versao]` |
| schema | `natureza: str` | VERMELHO: `test_economia_natureza_fixa_no_esquema` |
| schema | sem checagem `top_shap` x tipo | VERMELHO: `test_alerta_zscore_com_shap_ou_lightgbm_sem_shap_e_recusado` |
| schema | alvo da reducao fora da lista aceito | VERMELHO: `test_economia_exige_equipamento_alvo_na_lista` |
| schema | `strict=False` | rodada 1 VERDE (lacuna: `sensor_id=7` nao e coagivel); novo `test_valor_coagivel_nao_e_aceito_esquema_estrito`: VERMELHO |
| schema | NaN aceito (`allow_inf_nan=True`) | rodada 1 VERDE (o teste so cobria `tolerancia_pp`); novo `test_nan_em_campo_numerico_comum_e_recusado`: VERMELHO |
| artefato ausente | ausente vira `None` em vez de 503 | VERMELHO: `test_artefato_ausente_e_503`, `test_resumo_503_se_faltar_o_artefato_de_alertas` |
| artefato ausente | mensagem do 503 vaza o caminho | VERMELHO: `test_artefato_ausente_e_503` |
| artefato ausente | link simbolico para fora do diretorio aceito | VERMELHO: `test_sem_path_traversal_link_para_fora_do_diretorio_e_indisponivel` |
| artefato ausente | handler 503 devolve 500 | VERMELHO (varios testes) |
| filtros/limites | `ate` inclusivo; `de` exclusivo | VERMELHO: `test_alertas_filtro_de_ate_com_fuso` |
| filtros/limites | filtros de equipamento e de tipo ignorados | VERMELHO: `test_alertas_filtros_equipamento_e_tipo` |
| filtros/limites | `de >= ate` aceito | VERMELHO: `test_alertas_data_sem_fuso_e_de_depois_de_ate_sao_422` |
| filtros/limites | pagina com item a mais; ordem estavel quebrada | VERMELHO: `test_alertas_paginacao_cobre_tudo_sem_repetir` |
| filtros/limites | 422 ecoa o valor recebido | VERMELHO: `test_alertas_422_nao_ecoa_valor` |
| filtros/limites | limite maximo, limite minimo e offset negativo | rodada 1 VERDE na rota sozinha (defesa em profundidade: o caso de uso tambem valida); mutando rota e caso de uso juntos: VERMELHO (`test_alertas_limite_fora_de_1_a_500_e_422[100000]`, `[0]`, `test_alertas_offset_negativo_e_422`) |
| veredito | tolerancia sempre atendida | VERMELHO: `test_economia_veredito_derivado_dos_dados`, `test_veredito_muda_quando_os_dados_mudam` |
| veredito | so o alvo decide | rodada 1 VERDE (lacuna); novo `test_veredito_nao_atendido_quando_so_o_alvo_esta_dentro`: VERMELHO |
| veredito | tolerancia exclusiva (`<` em vez de `<=`) | rodada 1 VERDE (lacuna: nada na borda); novo `test_tolerancia_e_inclusiva_na_borda`: VERMELHO |
| veredito | erro sem subtrair o injetado | VERMELHO: `test_veredito_muda_quando_os_dados_mudam` |
| veredito | recuperado ausente conta como dentro | VERMELHO: `test_economia_veredito_derivado_dos_dados` |
| veredito | aviso D7 sempre dispara / nunca dispara | VERMELHO: `test_aviso_d7_derivado_nao_dispara_sem_feature_dominante` / `test_resumo_conteudo` |
| veredito | baseline fraca ignora os alertas | VERMELHO: `test_resumo_conteudo` |
| veredito | texto do veredito com a fracao injetada fixa (15.0) | rodada 1 VERDE (a fixture usava 15.0); novo `test_texto_do_veredito_usa_os_numeros_do_artefato`: VERMELHO |

Mutantes equivalentes (sobrevivem por desenho, nao por lacuna), todos de grupos que ficaram provados vermelhos por outra mutacao:

1. Sem cabecalho `Authorization` devolve `'x'` como segredo: `autenticar_empresa` rejeita `'x'`, continua 401.
2. Remover o filtro de tenant so em `resumo()`: o caso de uso exige `alertas` e `economia` da mesma empresa e devolve vazio do mesmo jeito.
3. `ConsultarResumoM3` sem exigir alertas/economia: o repositorio ja levanta 503 ao le-los.

Todos os grupos (401, tenant, esquema, artefato ausente, filtros/limites, veredito derivado) provados vermelhos. Nenhum grupo ficou sem prova.

Estado final (2026-10-01): `gtimeout 900 .venv/bin/pytest -W error -q`: 313 passed (304 anteriores + 2 de contrato + 7 casos novos da API); mypy strict em todos os pacotes e em `tests/m1`, `tests/m2`, `tests/m3`, `tests/contratos`: `Success: no issues found in 101 source files`; `lint-imports`: 9 kept, 0 broken.

## Antes x depois com grupo-controle

Dono: `domain/comparacao.py` (funcoes puras); `CompararAntesDepois` orquestra e `ExecutarM3` publica. O metodo antigo (baseline normalizado) continua no codigo e nos artefatos para comparacao.

**Metodo (diferenca em diferencas multiplicativa).** Economia % = `100 * (1 - R_tratado / R_controle)`, com `R = kWh depois / kWh antes`; o controle e a soma dos kWh dos controles escolhidos (so horas validas em todas as series). Contrafactual = `kWh_antes_tratado * R_controle`. A deriva de carga comum a todo o andar (ocupacao, calendario) entra nos dois lados da razao e cancela.

**Regra de escolha dos controles (`selecionar_controles`, fixada antes de ver o resultado, nao ajustada).** Candidatos = os outros equipamentos modelados do mesmo andar (um unico sensor), sem o tratado e, no varrimento, sem nenhum equipamento com reducao sintetica. Pontuacao = Pearson entre os perfis semanais (media horaria por semana de 168 h, semana valida com >= 90% das horas) do pre-periodo inteiro (2018-07-01 a 2018-11-18, antes da reducao). Fica quem tem correlacao >= 0.5; os 3 maiores; desempate por nome. Nenhum candidato passando = sem controle valido (resultado NaN com motivo, nunca um numero inventado). O tratado e excluido por construcao (teste dedicado).

**Resultado real (CU-BEMS 2018 Floor2, reducao sintetica de 15% em cada um dos 19 equipamentos, um por vez, tolerancia +-3 pp declarada antes):**

| Metodo | Dentro de +-3 pp | Erro abs. mediano | Erro abs. maximo | Alvo `z1_Light` |
|---|---|---|---|---|
| Baseline normalizado (antigo) | 7 de 19 | 6.71 pp | 18.90 pp | 27.18% (fora) |
| Diferenca em diferencas com controle (novo) | 12 de 19 | 1.88 pp | 13.09 pp | 17.14% (dentro) |

- Todos os 19 equipamentos acharam controle valido (`sem controle valido: nenhum`). Nenhuma baseline fraca (18 semanas completas de treino), entao nenhum equipamento marcado.
- **O novo metodo ainda falha em 7 de 19**: z1_Plug (10.20%), z2_AC10 (19.37%), z2_AC8 (19.28%), z2_Light (11.58%), z2_Plug (28.09%), z3_Light (9.59%), z3_Plug (8.12%). Nao e uma vitoria completa: a tolerancia nao foi alterada. z3_Plug passava no metodo antigo e saiu no novo.
- Controle sem reducao: economia espuria |media| 3.41% (antigo: 7.56%), maxima 15.41% (antigo: 22.24%, z2_Plug). Causa do residuo nao investigada; hipotese: controles que so correlacionam parcialmente com o tratado e equipamentos de pouco consumo (z2_Plug, 52 kWh no antes).
- Os controles de cada equipamento estao na ultima tabela de `data/m3/relatorio_m3.md` e em `economia.json` (`controles_usados`).
- Prova vermelha do teste (sem git): copia do teste em scratchpad com a afirmacao de recuperacao apontada para o metodo antigo: `1 failed` (obtido -19.2% contra 15% esperado, deriva sintetica comum de +40%); com o metodo novo passa. Testes: `tests/m3/domain/test_m3_controle.py` (8) e 1 de integracao.

**Artefatos.** `economia.json` e `resumo.json` mantem todos os campos e ganham campos opcionais: em `economia.json`, `metodo_recuperado_pct`, `metodo_controle`, `recuperado_pct_controle`, `dentro_da_tolerancia_controle` e, por equipamento, `recuperado_pct_controle`, `economia_pct_controle_sem_reducao`, `controles_usados`; em `resumo.json`, o bloco `antes_depois` (por metodo: recuperado no alvo, dentro no alvo, equipamentos dentro da tolerancia, sem resultado, erro mediano e maximo). O esquema estrito da plataforma (`extra="forbid"`) recusaria os campos novos; foram adicionados como opcionais em `src/mapen_plataforma/infrastructure/resultados_m3_json.py` (so validacao; o dominio da plataforma e a API ainda nao os expoem; "Contrato M3" nao mudou).

**Limites.** Os controles sao do mesmo andar e do mesmo periodo, entao a deriva especifica de um equipamento nao e removida; correlacao de perfil semanal com 20 semanas e uma estimativa ruidosa; sem temperatura. Continua sendo validacao de metodo com reducao sintetica, nao economia real.

## Estudo de previsao (2026-10-01)

Motivo: o LightGBM do M3 usa `kw_lag1`, entao e um nowcast de 1 passo, e 59.5% do SHAP esta nessa feature (D7). Comparar o MAE dele (0.2051 kW) com o baseline sazonal (0.6113 kW) nao e justo. Este estudo compara previsores sob um protocolo de previsao de verdade.

### Pre-registro (escrito ANTES de rodar qualquer previsor)

**Protocolo.** Por equipamento (os 19 modelados), mesmo subconjunto, mesmas dobras walk-forward (5 dobras de 2 semanas apos 8 semanas de treino inicial, dentro das 18 semanas 2018-07-01 a 2018-11-04) e o mesmo periodo reservado (2018-11-04 a 2018-12-02, 4 semanas). Origem da previsao = meia-noite; horizonte = as 24 horas do dia seguinte. Cada hora alvo `t` so pode usar observacoes de `t - 24 h` para tras.

**Regra de defasagem (obrigatoria).** Nenhuma feature da hora alvo `t` pode depender de um valor com defasagem menor que 24 h em relacao a `t`. Features permitidas: calendario (hora, dia da semana, feriado, hora da semana = tipo de dia x hora, com feriado como domingo), `kw_lag24`, `kw_lag48`, `kw_lag168`, media e desvio de 24 h calculados sobre a serie deslocada em 24 h. Sem `kw_lag1`. Cada hora alvo usa so dados disponiveis ate a meia-noite do seu dia. Guard: teste que perturba os valores com defasagem < 24 h e falha se alguma feature mudar (prova vermelha com uma feature violadora).

**Candidatos** (todos atras da porta `Previsor`): (1) seasonal-naive-168 e seasonal-naive-24; (2) baseline sazonal existente (media por hora da semana, feriado = domingo, ajustada na janela de treino); (3) Ridge com calendario one-hot, lags 24/48/168 e media/desvio 24 h sobre a serie deslocada 24 h (alpha escolhido dentro de cada ajuste por validacao cruzada temporal, `TimeSeriesSplit` de 5 particoes com folga de 24 h, grade 0.1, 1, 10, 100, so com dados anteriores ao fim do treino; o periodo reservado nunca participa); (4) ETS (statsmodels `ETSModel`, erro aditivo, sazonalidade aditiva de periodo 24, uma serie por tipo de dia: dia util, sabado, domingo/feriado; dias com qualquer hora ausente sao descartados da serie do tipo, nada e interpolado); (5) LightGBM por equipamento, hiperparametros ja existentes, so com as features permitidas.

**Metrica.** Sobre as horas do periodo reservado com alvo valido e previsao de todos os candidatos (suporte comum; o numero de horas e reportado). MAE, RMSE e MASE; MASE = MAE / escala, escala = MAE dentro da amostra do seasonal-naive-168 na janela de treino (pares com os dois valores validos). Todos os modelos sao ajustados nas 18 semanas de treino e avaliados nas 4 semanas reservadas; as dobras walk-forward sao desenvolvimento (reportadas, nao decidem) e fornecem o sigma do residuo fora da amostra para o benchmark. Previsao fisica: valores negativos sao truncados em 0 kW para todos os candidatos.

**Regra de decisao.** "Adotado para previsao" so se, no periodo reservado: (a) a mediana (entre equipamentos) do MASE do modelo e pelo menos 10% menor que a do seasonal-naive-168 (mediana_modelo <= 0.90 x mediana_naive168), E (b) o modelo vence o seasonal-naive-168 (MASE menor no mesmo equipamento) em pelo menos 12 dos 19 equipamentos. Se varios passam, vale o mais simples dentro de 5% da melhor mediana entre os que passaram. Se nenhum passa, adota-se o modelo mais simples cuja mediana de MASE esteja dentro de 5% da melhor mediana de todos os candidatos (mediana <= 1.05 x melhor). Ordem de simplicidade: seasonal-naive-24 < seasonal-naive-168 < baseline sazonal < Ridge < ETS < LightGBM. Contagem de vitorias por melhor-de-todos tambem e reportada, mas nao entra na regra.

**SHAP / D7 (LightGBM de previsao).** Participacao no |SHAP| medio no periodo reservado, por grupo (calendario, lags, janela movel) e por feature; flag D7 se uma unica feature passa de 50%.

**Benchmark sintetico.** Mesmas anomalias injetadas (mesma semente e mesmo gerador do benchmark existente), detector = |residuo do previsor adotado| / sigma >= 4, sigma = desvio dos residuos fora da amostra das dobras walk-forward. Rotulado SINTETICO.

### Implementacao (arquitetura em camadas, mesmas quatro camadas do M3)

| Arquivo | Camada | Dono de |
|---|---|---|
| `domain/previsao.py` | domain | protocolo (origem meia-noite, 24 h), features permitidas, `naive_sazonal`, guard `defasagem_violadora` |
| `domain/metricas_previsao.py` | domain | MAE, RMSE, MASE, suporte comum, `decidir_adocao` (a regra pre-registrada), participacao SHAP por grupo |
| `application/portas.py` | application | porta `Previsor` (e `PrevisorExplicavel`) |
| `application/estudo_previsao.py` | application | `EstudoPrevisao`: dono do ciclo (dobras, reservado, decisao, SHAP, benchmark) |
| `application/benchmark_previsao.py`, `application/injecao_periodo.py` | application | benchmark sintetico com residuo do previsor; injecao compartilhada com `BenchmarkSintetico` (consolidada, mesmo gerador, mesma semente) |
| `infrastructure/previsores_simples.py`, `previsor_ridge.py`, `previsor_ets.py`, `previsor_lightgbm.py` | infrastructure | adaptadores `Previsor` (naive 24/168, baseline sazonal, Ridge, ETS, LightGBM) |
| `interface/artefatos_previsao.py`, `interface/cli_previsao.py` | interface | `previsao.json`, `relatorio_previsao.md` e CLI (`python -m mapen_modelos.interface.cli_previsao`) |

`sklearn` e `statsmodels` entraram na lista de modulos proibidos em domain/application (import-linter). `statsmodels` foi adicionado a `pyproject.toml`; `sklearn.*` e `statsmodels.*` ganharam `ignore_missing_imports` no mypy (as duas bibliotecas nao publicam `py.typed`).

Decisoes de implementacao do ETS: periodo 168 descartado (168 estados sazonais, 18 ciclos de treino, estimacao instavel e lenta); usado periodo 24 com uma serie por tipo de dia (dia util, sabado, domingo/feriado), dias com qualquer hora ausente descartados da serie do tipo (sem interpolacao), parametros estimados uma vez por tipo no treino e filtro reaplicado (`smooth`) a cada dia alvo sobre os dias anteriores. Serie de treino constante (log de variancia zero, `RuntimeWarning` do statsmodels): o previsor repete o ultimo dia do tipo. O statsmodels emitia `ConvergenceWarning` com o `maxfun` padrao (15000 avaliacoes de funcao, gradiente numerico de ~27 parametros; reproduzido em z2_Light, dia util); a causa foi corrigida com `maxiter=1000`, `maxfun=100000` e nao ha `filterwarnings`. Nota: o statsmodels registra `simplefilter("always", ConvergenceWarning)` ao importar, entao `-W error` nao transforma esse aviso em erro; o adaptador conta ajustes sem convergencia (`ajustes_sem_convergencia`) e o CLI os poe em `avisos`. Execucao real: 0 ajustes sem convergencia. Importar `statsmodels` e `sklearn` sob `-W error` nao emite aviso nenhum.

### Resultados reais (execucao de 2026-10-01, ~5 min; relatorio completo em `data/m3/relatorio_previsao.md`, gitignored)

Periodo reservado (2018-11-04 a 2018-12-02), 19 equipamentos, 12.571 horas-equipamento no suporte comum (alvo valido e previsao de todos os candidatos). Modelos ajustados nas 18 semanas de treino, sem reajuste durante o periodo reservado.

| Modelo | MAE agregado (kW) | Mediana MASE | Mediana MASE (dobras, desenvolvimento) | Vitorias vs naive-168 | Melhor de todos em |
|---|---|---|---|---|---|
| seasonal-naive-24 | 0.5006 | 0.7293 | 0.9201 | 9/19 | 9 |
| **seasonal-naive-168** | **0.1185** | **0.5089** | 0.8970 | - | 9 |
| baseline sazonal (media por hora da semana) | 0.5107 | 1.7505 | 1.1632 | 0/19 | 0 |
| Ridge | 0.3089 | 0.6941 | 0.9584 | 7/19 | 0 |
| ETS-24 por tipo de dia | 0.4044 | 0.8217 | 1.2096 | 2/19 | 0 |
| LightGBM (lag >= 24 h) | 0.2536 | 0.6602 | 0.9740 | 4/19 | 1 |

MAE, RMSE e MASE por modelo e equipamento: `previsao.json` (`metricas_reservado`) e `relatorio_previsao.md`.

**Desfecho da regra pre-registrada: nenhum candidato passou.** Nenhum chega a 10% abaixo da mediana do seasonal-naive-168 (todos estao acima dela) e o melhor ganho de vitorias e 9 de 19 (naive-24, e Ridge 7 de 19), longe de 12. O LightGBM NAO ganha: mediana de MASE 0.6602 contra 0.5089 do naive-168 (30% pior), 4 vitorias de 19. Pela regra de fallback, o modelo adotado e o **seasonal-naive-168**, que tambem e o de melhor mediana.

Leitura honesta. (1) O 0.2051 kW contra 0.6113 kW do M3 era uma comparacao entre nowcast e baseline estatico; sob protocolo de previsao do dia seguinte, o baseline sazonal estatico e o PIOR candidato (mediana de MASE 1.75), e o naive-168 (MAE agregado 0.1185 kW) bate todos. (2) A causa e deriva de regime, nao bug: p.ex. z2_AC5 liga e desliga em horarios que mudaram durante os 5 meses; a media por hora da semana de 18 semanas mistura os dois regimes (esperado 0.7 kW em horas em que a carga real e 0), enquanto o naive-168 copia a semana passada. Os candidatos treinados uma vez nas 18 semanas nao se adaptam; o naive-168 se adapta por construcao. (3) Isso e uma propriedade do protocolo pre-registrado (modelos fixos no periodo reservado), nao prova que um modelo com reajuste semanal tambem perderia; nao testado (ver "Nao feito"). (4) Em z2_AC10, AC2, AC3, AC4, AC6 e AC8 o naive-24 fica abaixo do naive-168 em MASE (0.50 a 0.57 contra 0.61 a 0.71), mas isso so da 9 vitorias de 19 e a mediana continua pior.

**SHAP / D7 (LightGBM de previsao, periodo reservado, 12.571 horas-equipamento).** Calendario 32.0% (hora 12.2%, dia da semana 9.5%, hora da semana 10.0%, feriado 0.3%), lags 61.5% (`kw_lag168` 30.2%, `kw_lag24` 23.9%, `kw_lag48` 7.3%), janela movel 6.6%. **O flag D7 de feature unica > 50% NAO dispara no agregado** (a maior e `kw_lag168`, 30.2%): a tautologia de `kw_lag1` (59.5%) some sem o lag 1. Por equipamento dispara em 6 de 19 (z2_AC10, AC5, AC6, AC7, AC8, AC9). Nota: o LightGBM sem lag 1 tambem nao passa o naive-168; a atribuicao ficar mais equilibrada nao o torna melhor.

**Benchmark SINTETICO com o residuo do previsor adotado (seasonal-naive-168).** Mesma semente (20181104), mesmos 114 eventos, mesmo limiar |z| >= 4, sigma = desvio do residuo fora da amostra nas 5 dobras (um valor por equipamento). Rotulado SINTETICO: nao e precisao/recall em dado real.

| Detector | Pico | Elevacao fora de horario | Ligado continuo | Total | Falso alarme |
|---|---|---|---|---|---|
| z-score sazonal (existente) | 38/38 (100%) | 19/38 (50.0%) | 27/38 (71.1%) | 84/114 (73.7%) | 114/9145 (1.2%) |
| LightGBM nowcast, lag 1 (existente) | 38/38 (100%) | 22/38 (57.9%) | 30/38 (78.9%) | 90/114 (78.9%) | 45/9145 (0.5%) |
| residuo do seasonal-naive-168 | 38/38 (100%) | 0/38 (0.0%) | 17/38 (44.7%) | 55/114 (48.2%) | 3/7266 (0.04%) |

Leitura: o naive-168 e um detector muito conservador (poucos falsos alarmes) e quase cego as elevacoes de madrugada, porque um sigma unico por equipamento, calibrado no residuo diurno, e grande demais para o ruido de madrugada (os dois detectores existentes usam sigma por hora da semana ou nowcast). A zona excluida do falso alarme e maior que a do benchmark original (um evento contamina as horas p, p+1 a p+48 e p+168, porque a janela dos features cobre [t-47, t-24]); por isso o denominador e 7.266, nao 9.145, e o falso alarme nao e comparavel ponto a ponto. Compartilhar o gerador de eventos deixou os numeros do benchmark original intactos (testes de integracao existentes verdes).

### Esquema de `data/m3/previsao.json` (gitignored; NAO e lido pela API ainda)

`{versao_esquema: 1, sensor_id, natureza: "estudo_previsao_dia_seguinte", aviso, protocolo{origem, horizonte_h, defasagem_minima_h, treino{inicio,fim}, reservado{inicio,fim}, dobras_walk_forward, referencia_mase}, equipamentos[], sem_carga[], modelos[], metricas_reservado{modelo{equipamento{mae_kw, rmse_kw, mase, horas}}}, mae_agregado_kw{modelo}, mediana_mase_reservado{modelo}, mediana_mase_desenvolvimento{modelo}, vitorias_vs_naive168{modelo}, vitorias_melhor_de_todos{modelo}, decisao{regra_aplicada, adotado, passaram_regra_de_ganho[], melhor_mediana, motivo}, mase_por_equipamento{modelo{equipamento}}, avisos[], shap_lightgbm{participacao_por_feature{}, participacao_por_grupo{calendario, lags, janela_movel}, d7_feature_dominante, d7_flag, equipamentos_com_flag[], horas}, benchmark_sintetico{sintetico: true, previsor, semente, eventos_por_tipo_por_equipamento, limiar_z, injetados{tipo}, detectados{tipo}, taxa_deteccao, taxa_deteccao_por_tipo{}, alertas_fora_da_zona, horas_fora_da_zona, taxa_falso_alarme}}`. NaN vira null; MAE/RMSE/MASE e taxas com 4 casas.

### Testes do estudo

`tests/m3/domain/test_m3_previsao.py` (guard de defasagem, lacuna, naive, MASE, regra de decisao), `tests/m3/infrastructure/test_m3_previsores.py` (um teste por previsor em serie sintetica de estrutura conhecida, nao enxergar dados a partir da meia-noite para os 6 previsores, lacuna: Ridge so deixa NaN onde o lag falta, ETS descarta o dia com lacuna, ETS com serie constante, contribuicoes SHAP), `tests/m3/application/test_m3_estudo_previsao.py` (ciclo completo sintetico, serializacao sem NaN).

**Prova vermelha do guard de defasagem (sem git).** `test_nenhuma_feature_de_previsao_usa_defasagem_menor_que_24h` usa `CONSTRUTOR = montar_features_previsao`. Copia do arquivo de teste em `/private/tmp/.../scratchpad/red/` com `CONSTRUTOR = construtor_violador` (acrescenta `kw_lag1 = kw.shift(1)`):

```
E         Left contains one more item: 'kw_lag1'
FAILED test_red_previsao.py::test_nenhuma_feature_de_previsao_usa_defasagem_menor_que_24h
1 failed, 13 deselected
```

1 caso falhou (o guard); com o construtor real, os 14 testes do arquivo passam. Os testes `test_guard_detecta_lag1` e `test_guard_detecta_janela_movel_sem_deslocamento` mostram que o guard pega tambem uma janela movel sem o deslocamento de 24 h. Nao-vazamento dos adaptadores: `test_previsao_do_dia_nao_enxerga_dados_a_partir_da_meia_noite` (6 previsores). Este ultimo nao foi visto vermelho contra um adaptador quebrado.

### Nao feito / limites do estudo

1. Modelos fixos no periodo reservado (ajustados uma vez em 18 semanas); nao foi testado reajuste semanal/expansivo, que e o que um sistema real faria e que pode mudar a classificacao de Ridge e LightGBM frente ao naive-168. Seria um estudo novo com regra pre-registrada nova.
2. Sigma unico por equipamento no benchmark do naive-168 (sem sigma por hora); sensibilidade a elevacoes de madrugada ficou em 0%.
3. Um andar, 22 semanas, uma unica janela reservada de 4 semanas; a classificacao pode mudar com outra janela.
4. Os artefatos de alerta, economia e resumo e a API nao foram alterados; o `previsao.json` ainda nao e consumido por nenhum adaptador da plataforma.
5. ETS usa periodo 24 com tipo de dia, nao periodo 168 (justificativa acima).

## Alertas z-score com seasonal-naive-168 e escala semanal (2026-10-02)

Motivo: o estudo de previsao mostrou que o baseline sazonal estatico (media por hora da semana, 18 semanas fixas) e o pior candidato (mediana de MASE 1,75) e que o naive-168 e o adotado. Os alertas z-score usavam justamente o baseline pior. Mudou so o detector z-score; LightGBM, MAE da tabela, SHAP e antes x depois seguem como estavam.

**Regra** (`domain/baseline_naive.py`, funcao `zscore_naive168`): esperado = valor observado 168 h antes; z = (observado - esperado) / sigma; sigma = desvio dos residuos `obs(t) - obs(t-168)` na mesma hora da semana (168 posicoes, posicao = dia da semana x 24 + hora, feriado NAO vira domingo), com o mesmo piso do baseline antigo (5% do nivel medio, minimo 0,01 kW) e queda para o desvio global com menos de 3 amostras. **Refit semanal**: o periodo reservado e dividido em blocos de 168 h a partir de 2018-11-04; o sigma de cada bloco usa so residuos anteriores ao inicio do bloco (historico expansivo desde o inicio do treino). Residuos de horas que ja viraram alerta ficam de fora das semanas seguintes. `baseline_fraca` = menos de 4 semanas completas de residuo no historico (nenhum alerta real ficou fraco). `janela_baseline` do alerta = do inicio do treino ao inicio da semana do alerta. O limiar (|z| >= 4) nao foi alterado.

**O que nao se refaz:** o naive-168 nao tem parametro; adapta-se a deriva por construcao. LightGBM e Ridge continuam fixos (reajuste semanal deles segue em "Nao feito" do estudo de previsao).

**Efeito colateral documentado:** o residuo carrega o valor de 168 h antes, entao um evento isolado alerta duas vezes (na hora e uma semana depois, com sinal oposto). E o mesmo contorno da zona contaminada do benchmark. Feriado nacional tambem gera alerta (15/11/2018 teve 3 de z-score), porque o esperado e a mesma hora da semana passada.

### Resultado real (CU-BEMS 2018Floor2, mesmo periodo reservado, mesma semente 20181104)

| | Antes (media por hora da semana) | Depois (naive-168 + escala semanal) |
|---|---|---|
| Alertas z-score no dado real (candidatos, 0 corroborados) | 160 | 128 |
| Benchmark sintetico, deteccao total | 84/114 (73,7%) | 88/114 (77,2%) |
| Pico | 38/38 | 38/38 |
| Elevacao fora de horario | 19/38 | 19/38 |
| Ligado continuo | 27/38 | 31/38 |
| Falso alarme (horas fora da zona, limite superior) | 114/9145 (1,25%) | 99/9145 (1,08%) |

LightGBM (alertas e benchmark) saiu identico: 54 alertas, 90/114, 44/9145. Leitura honesta: o ganho e pequeno (+4 eventos de 114, -15 horas de falso alarme) e vem do ligado continuo; a elevacao fora de horario continua em 50% porque a escala por hora da semana ainda e dominada pela variancia das cargas variaveis. O benchmark e SINTETICO, nao e precisao/recall em dado real. A injecao continua usando a escala P95 do aquecimento de 168 h antes do periodo (numeros do gerador inalterados); o historico completo do treino so alimenta a escala do z-score.

Testes: `tests/m3/domain/test_m3_baseline_naive.py` (esperado = 168 h antes, pico, lacunas, escala sem uso do futuro, refit por semana, censura de alertas, janela/baseline fraca). Prova vermelha por variantes quebradas do modulo (copias em scratchpad, sem git): sem censura = 2 testes falham; escala calculada com a serie inteira (vazamento do futuro) = 4 testes falham; com o modulo real, 8 passam.
