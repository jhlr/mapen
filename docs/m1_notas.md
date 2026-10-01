# M1 notas de implementacao (2026-10-01)

Pacote `src/mapen_aconselhamento/` (ingest, tarifa, custo, ranking, recomenda, relatorio). Todos os numeros abaixo vem de execucoes reais nesta sessao.

## Prova vermelha do teste da lacuna (sem git)

`tests/test_ingest.py` tem a referencia posicional ingenua `_defasar_posicional` (`serie.shift(n)`) e o mesmo corpo de teste (`_lacuna_nao_pulada`) roda contra ela e contra `ingest.defasar` (reindexa ao calendario completo e depois faz shift). A serie tem 2 pontos consecutivos faltando (t2, t3). Contra a referencia ingenua o teste esta marcado `xfail(strict=True)`: se ela um dia passasse, a suite quebra.

Executando com `pytest --runxfail tests/test_ingest.py -v`:

```
tests/test_ingest.py::test_reindexar_marca_lacuna_sem_interpolar PASSED
tests/test_ingest.py::test_lag_nao_pula_lacuna PASSED
tests/test_ingest.py::test_referencia_posicional_falha_no_teste_da_lacuna FAILED
FAILED tests/test_ingest.py::test_referencia_posicional_falha_no_teste_da_lacuna
========================= 1 failed, 2 passed in 0.51s ==========================
```

A falha da referencia ingenua: o indice do resultado nao contem t3 (`DatetimeIndex(['...00:00', '...01:00', '...04:00', '...05:00'])`) e o lag de t4 vira 2.0 (valor de t1), pulando a lacuna. Contra `defasar` os dois testes passam.

Execucao normal da suite:

```
tests/test_custo.py::test_custo_convencional_fixture_24h PASSED
tests/test_custo.py::test_custo_branca_fixture_24h PASSED
tests/test_custo.py::test_pontos_ausentes_nao_entram_no_custo PASSED
tests/test_custo.py::test_top_n_ordena_por_custo PASSED
tests/test_ingest.py::test_reindexar_marca_lacuna_sem_interpolar PASSED
tests/test_ingest.py::test_lag_nao_pula_lacuna PASSED
tests/test_ingest.py::test_referencia_posicional_falha_no_teste_da_lacuna XFAIL
tests/test_integracao.py::test_amostra_real_cu_bems_ate_relatorio PASSED
tests/test_integracao.py::test_bdg2_le_direto_do_zip PASSED
tests/test_recomenda.py::test_recomenda_somente_flexivel PASSED
tests/test_recomenda.py::test_sem_economia_quando_origem_ja_e_a_mais_barata PASSED
tests/test_recomenda.py::test_config_yaml_marca_ac_flexivel_e_iluminacao_nao PASSED
tests/test_tarifa.py::test_convencional_preco_unico PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 15:59-0.66447] PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 16:00-1.05341] PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 17:59-1.05341] PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 18:00-1.62479] PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 20:59-1.62479] PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 21:00-0.66447] PASSED
tests/test_tarifa.py::test_branca_preco_por_horario[2026-10-05 00:00-0.66447] PASSED
tests/test_tarifa.py::test_branca_fim_de_semana_sempre_fora_de_ponta PASSED
======================== 20 passed, 1 xfailed in 1.83s =========================
```

mypy (`strict = true`, `files = src/mapen_aconselhamento`): `Success: no issues found in 7 source files`.

## Relatorio real

CU-BEMS andar 2, 2018-08 (1.071.360 linhas em `leitura`, 7.802 ausentes), gerado em `data/relatorios/cu_bems_2018Floor2_2018-08.md` (gitignored). Primeiras linhas:

```
# Relatorio de custo de energia: cu_bems_2018Floor2, 2018-08

> **Aviso:** Curva de carga estrangeira + tarifa brasileira = demonstracao de metodo. Este relatorio nao mostra o comportamento de carga no Brasil e nao e aconselhamento a cliente.

- Dados: CU-BEMS andar 2, 2018-08 (Pipattanasomporn et al. 2020, CC BY 4.0).
- Tarifa: Neoenergia PE, REH 3.583/2026, subgrupo B3, sem tributos e sem bandeira.
- Pontos ausentes (sem interpolacao, fora do custo): 7802 de 1071360 (0.7%). Com lacunas, os custos abaixo sao um piso.
- Custo total, convencional: R$ 17725.21.
- Custo total, branca: R$ 17333.72.

## Top 5 equipamentos por custo (convencional)

| # | Equipamento | kWh | Custo convencional (R$) | Custo branca (R$) | Flexivel |
|---|---|---|---|---|---|
| 1 | z1_AC1 | 7142.7 | 5705.99 | 5823.74 | sim |
| 2 | z2_AC1 | 3304.4 | 2639.74 | 2362.13 | sim |
| 3 | z1_Light | 2580.5 | 2061.43 | 2160.55 | nao |
| 4 | z4_AC1 | 2148.9 | 1716.70 | 1553.58 | sim |
| 5 | z1_Plug | 916.6 | 732.23 | 697.96 | nao |

## Recomendacoes: mover carga flexivel (tarifa branca)

Economia = kWh movido x (preco da faixa de origem - preco da faixa de destino). O kWh movido e a fracao do cenario em `config/equipamentos.yaml` (hipotese, nao medicao). Cargas nao marcadas `flexivel` nao tem economia calculada.

| Equipamento | De | Para | kWh movido | Economia no mes (R$) |
|---|---|---|---|---|
| z1_AC1 | ponta | fora_ponta | 148.36 | 142.47 |
| z1_AC1 | intermediario | fora_ponta | 187.84 | 73.06 |
| z2_AC1 | intermediario | fora_ponta | 64.41 | 25.05 |
| z4_AC1 | intermediario | fora_ponta | 44.76 | 17.41 |
| z2_AC5 | ponta | fora_ponta | 17.44 | 16.74 |
| z2_AC9 | ponta | fora_ponta | 12.95 | 12.44 |
```

BDG2 (custo de predio inteiro): `carregar_bdg2` le o CSV direto do zip; verificado com o medidor `Panther_parking_Lorriane`, 2016-08 (744 horas, 0 ausentes, 8.163,7 kWh, R$ 6.521,63 convencional, R$ 6.361,09 branca). Demonstracao de metodo, nao consumo brasileiro.

## Pontos de atencao e suposicoes

1. `leitura` tem uma 7a coluna `ausente BOOLEAN`, alem das 6 do spec, para carregar a flag de lacuna.
2. `sensor_id` = identificador do predio/andar (ex.: `cu_bems_2018Floor2`); `equipamento_id` = coluna do CU-BEMS sem unidade (ex.: `z2_AC1`; ids de zona se repetem entre andares, o predio e distinguido pelo `sensor_id`). No BDG2, `sensor_id` = nome do medidor e `equipamento_id` = `geral`. `tensao_v` fica NULL (datasets nao tem tensao).
3. Tarifa: so os 4 valores do B3 (convencional, branca ponta/intermediario/fora de ponta) foram convertidos, todos presentes e verificaveis em `docs/regulacao/tarifas_neoenergia_pe.md`. Grupo A, reativo e B1 ficaram fora (nao usados). Tarifas sem tributos e sem bandeira; REH 3.583 nao conferida no PDF da ANEEL (pendencia do doc de regulacao).
4. Horarios da branca: ponta 18-20:59, intermediario 16-17:59, resto fora de ponta, fins de semana fora de ponta. A janela intermediaria apos a ponta (21h) nao esta confirmada no doc; tratada como fora de ponta. Feriados nao modelados (sem calendario).
5. `config/equipamentos.yaml`: AC flexivel com `fracao_movivel: 0.2`, iluminacao e tomadas nao flexiveis. Isso e hipotese de cenario para a demonstracao, nao medicao nem dado de cliente; a economia do relatorio e kWh da faixa x 20% x (preco origem - preco destino). Destino fixo: fora de ponta.
6. `.gitignore`: `data/` era ignorado por inteiro, o que esconderia `data/tarifas/neoenergia_pe.csv` (arquivo do spec). Troquei para `data/*` mais `!data/tarifas/`; o resto de `data/` continua ignorado. `.venv/` e `data/relatorios/` estao ignorados (conferido com `git check-ignore`).
7. O zip do BDG2 tem pasta raiz com hash (`buds-lab-...-3d0cbaf/`), entao o caminho `data/meters/cleaned/electricity_cleaned.csv` citado em `docs/datasets_publicos.md` e casado por sufixo.
8. CU-BEMS: custo calculado com kWh = kW x 1/60 h por minuto. Pontos ausentes nao entram no custo (piso). O doc de datasets fala em dados faltantes nos andares 3 e 4; o andar 2 de 2018-08 teve 0,7% de pontos ausentes.
9. `shap` e `pyyaml` adicionados as dependencias; `mypy`, `pandas-stubs`, `types-PyYAML` no extra `dev`. `shap` nao e usado no M1 (so exigido pelo spec).
10. Teste de integracao usa 1 semana real do CU-BEMS andar 2 e pula (`skipif`) se o dataset nao estiver baixado.

## Criterios de aceite

Todos os 7 atendidos: (1) `pip install -e .` e `import mapen_aconselhamento` ok; (2) custo da fixture 24 h dentro de R$ 0,01 (convencional 38,35, branca 39,21, calculo manual no teste); (3) teste da lacuna vermelho contra o shift posicional e verde contra a reindexacao; (4) relatorio real com top-5, custo em R$ e recomendacoes; (5) recomendacao so para `flexivel` (e nao `critico`); (6) disclaimer no relatorio; (7) testes verdes.
