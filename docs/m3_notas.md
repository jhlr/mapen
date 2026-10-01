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
| `application/executar_m3.py` | application | `ExecutarM3`: dono do ciclo completo |
| `infrastructure/serie_duckdb.py` | infrastructure | leitor de series horarias sobre a tabela `leitura` do M1 |
| `infrastructure/subconjunto.py` | infrastructure | carga do subconjunto com o carregador do M1 (`carregar_cu_bems`) |
| `infrastructure/lightgbm_modelo.py` | infrastructure | regressor LightGBM por equipamento |
| `infrastructure/shap_explicador.py` | infrastructure | valores SHAP (ver "Limites" sobre o pacote `shap`) |
| `infrastructure/arquivos.py` | infrastructure | gravacao de relatorio e JSON |
| `interface/relatorio_markdown.py`, `interface/artefatos_json.py`, `interface/cli.py` | interface | relatorio, esquemas JSON e CLI |

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

`alertas.json`: `{versao_esquema, sensor_id, periodo{inicio,fim}, limiar_z, aviso, alertas[]}`; cada alerta: `equipamento` (str), `timestamp` (ISO, ingenuo), `tipo` (`zscore` | `lightgbm`), `esperado_kw`, `observado_kw`, `z` (float; no LightGBM e o residuo / desvio fora da amostra das dobras), `janela_baseline{inicio,fim}` (janela de treino), `top_shap` (null no z-score; no LightGBM lista de 3 `{feature, shap}`), `baseline_fraca` (bool), `status` (sempre `candidato_nao_corroborado`).

`economia.json`: `{versao_esquema, sensor_id, natureza: "validacao_de_metodo_sintetica", aviso, periodo_antes, periodo_depois, reducao_sintetica{equipamento, fracao_pct, a_partir_de}, recuperado_pct, tolerancia_pp, dentro_da_tolerancia, equipamentos[]}`; cada equipamento: `equipamento`, `kwh_antes`, `kwh_depois`, `kwh_contrafactual`, `economia_kwh`, `economia_pct` (com a reducao no equipamento alvo), `economia_pct_sem_reducao` (controle), `recuperado_pct_com_reducao_sintetica` (varredura), `reducao_sintetica_aplicada` (bool), `baseline_fraca` (bool). Valores NaN viram null. Nao ha R$: so kWh.

## Testes

`tests/m3/` (43 testes): unitarios por peca de dominio, guard de vazamento, teste de lacuna (lags e janela NaN no ponto certo; treino nunca recebe alvo NaN), integracao sintetica de semente fixa (benchmark e antes x depois), leitor DuckDB e explicador. Suite completa `gtimeout 900 .venv/bin/pytest -W error -q`: 256 passed (213 anteriores + 43). mypy strict (`src/mapen_modelos`, `tests/m3`, e os demais): `Success: no issues found in 95 source files`.

## Limites e o que NAO esta validado

1. Sem rotulo: nenhuma precisao/recall em dado real. Taxas de deteccao e falso alarme valem so para as anomalias injetadas (tipos, magnitudes e semente deste benchmark).
2. Economia: nao ha intervencao real. O metodo falhou a tolerancia em dado real com deriva (27.18% recuperado para 15% injetado). Melhorias candidatas, nao feitas: covariaveis de temperatura/ocupacao (CU-BEMS tem temperatura, o carregador do M1 ignora), grupo de controle concorrente, janelas mais longas. Normalizacao por temperatura nao implementada.
3. R$ nao calculado no antes x depois (so kWh).
4. D7: o lag 1 domina o SHAP; o LightGBM e um nowcast. Um alerta de LightGBM tem pouca sensibilidade a anomalias persistentes porque o lag 1 as absorve apos a primeira hora.
5. `shap` nao e importado: o pacote 0.52 emite `PendingDeprecationWarning` (matplotlib) na importacao, o que quebra `-W error`, e o aviso e de codigo de terceiros. O adaptador usa a contribuicao TreeSHAP nativa do LightGBM (`pred_contrib=True`), que e o mesmo algoritmo; conferido contra `shap.TreeExplainer` com diferenca maxima 0.0 em valores e valor base. `shap` continua em `pyproject.toml`. `lightgbm` e `shap` ja estavam listados; nenhuma dependencia nova.
6. Limiar |z| >= 4 e hiperparametros do LightGBM fixos, nao ajustados em dado rotulado. Sigma do LightGBM vem do desvio dos residuos fora da amostra das dobras.
7. Um unico andar e 22 semanas de 2018; so predio universitario tropical. Nao generaliza para o piloto.
8. Timestamps ingenuos; feriados so nacionais (lista do M1). Dias letivos/ferias nao entram.
