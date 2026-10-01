# M1 notas de implementacao (2026-10-01)

Pacote `src/mapen_aconselhamento/` (ingest, tarifa, custo, ranking, recomenda, relatorio). Todos os numeros abaixo vem de execucoes reais nesta sessao.

## Revisao adversarial e premissas com fonte (2026-10-01, segunda rodada)

Insumos: revisao adversarial do M1 e `docs/m1_premissas.md`. Todos os numeros abaixo vem de execucoes reais.

### O que mudou

1. `ingest.defasar` e seus testes foram removidos. Nao tinha chamador em nenhum caminho de feature e a prova vermelha antiga estava errada (a referencia ingenua falhava por indice sem `t3`, nao por pular a lacuna). Sem feature de lag no M1, ligar a funcao seria inventar escopo; quando existir feature de lag, o teste deve reindexar ao calendario completo, afirmar o NaN no ponto da lacuna e comparar o shift posicional com o lag real. Como a funcao saiu, nao ha linha de asserção falhando para mostrar. Ficou so `test_reindexar_marca_lacuna_sem_interpolar`.
2. Timestamps duplicados: `tratar_duplicados` conta as repeticoes. Padrao `duplicados="erro"` levanta `TimestampsDuplicadosError` com a contagem; `duplicados="primeiro"` mantem a primeira ocorrencia e grava a contagem na tabela `ingestao`, que o relatorio le ("Timestamps duplicados: N descartados"). Ressalva de timestamps ingenuos e horario de verao no relatorio.
3. Tarifa: ponta 18:00-20:59, intermediario 16:00-17:59; 21h e a chave `hora_21_intermediaria` (padrao fora de ponta, relatorio diz que nao esta confirmado). Fins de semana e os 11 feriados nacionais da lista do doc sao fora de ponta (calendario explicito com `dateutil.easter`). A biblioteca `holidays` (0.105) NAO bate com a lista: inclui 20/nov, vesperas de Natal e Ano Novo, quarta de cinzas, segunda de carnaval e facultativos; por isso nao foi adotada. `python-dateutil` entrou nas dependencias.
4. `fracao_movivel` e validada no carregamento (finita, 0 < f <= 1; regra flexivel exige o valor; baixa <= central <= alta). Valores sourced: central 0.18 (Ruud 1990 via LBNL 2006), baixa 0.10, alta 0.25 (Keeney e Braun 1997 via LBNL 2006). O relatorio mostra as tres economias, com coluna "Economia sob hipotese de X% movel" e ressalva de que a faixa e de predios dos EUA, sem medicao brasileira.
5. `% ausente` por equipamento no ranking (`ranking.pct_ausente_por_equipamento`, argumento de `top_n`).
6. `Tarifas.carregar`: chave (modalidade, posto) unica por vigencia (erro se repetida), selecao por data de referencia (obrigatoria se houver mais de uma vigencia; erro se nenhuma vigente).
7. `gross_up` (multiplicativo, >= 1) e `bandeira_rs_kwh` (>= 0) opcionais, vazios por padrao. Preco usado = (base + bandeira) x gross_up. O relatorio diz se os valores sao "SEM tributos e SEM bandeira".
8. Teste de integracao sintetico (CSV no formato CU-BEMS, outubro/2026, com 1 h de lacuna e o feriado de 12/out) com numeros exatos e linhas de recomendacao; o teste com dado real continua, pula se `data/publicos` faltar, e agora carrega o mes inteiro que o relatorio usa (2018-08).
9. `config/equipamentos.yaml`: glob `*_AC[0-9]*` (nao casa `z1_ACCESS`); testes dos valores de `critico` e `fracao_movivel`.
10. `.gitignore`: `data/*`, `!data/tarifas/`, `data/tarifas/*`, `!data/tarifas/neoenergia_pe.csv`. A linha de diretorio e necessaria: o git nao reabilita arquivo dentro de diretorio excluido. Conferido com `git check-ignore`: so o CSV de tarifas fica rastreavel.

### Resultados

pytest: `53 passed in 5.28s` (inclui o teste real do CU-BEMS; tambem verde com `-W error`). mypy (`strict`, `src/mapen_aconselhamento`): `Success: no issues found in 7 source files`.

### Relatorio real: antes e depois (CU-BEMS andar 2, 2018-08)

| Item | Antes | Depois |
|---|---|---|
| Custo convencional | R$ 17725.21 | R$ 17725.21 |
| Custo branca | R$ 17333.72 | R$ 17333.72 |
| Pontos ausentes | 7802 de 1071360 (0.7%) | igual; agora por equipamento (z1_AC1 0.7%, z2_AC1 0.8%) |
| Fracao movivel | 20% (inventada) | 18% central (10%/25% como faixa) |
| Economia total no mes | R$ 355.70 | R$ 320.15 (18%); R$ 177.86 (10%); R$ 444.65 (25%) |
| Linhas de recomendacao | 28 | 28 |
| z1_AC1, ponta -> fora de ponta | R$ 142.47 | R$ 128.22 (R$ 71.24 a R$ 178.09) |

Custos nao mudaram porque agosto de 2018 nao tem feriado nacional da lista e o padrao de 21h (fora de ponta) e o mesmo de antes. A economia caiu so pela troca 20% -> 18%. Relatorio: `data/relatorios/cu_bems_2018Floor2_2018-08.md` (gitignored).

### Nao feito

1. Gross-up e bandeira ficam vazios: aliquota de ICMS e bandeira vigente nao foram encontradas (docs/m1_premissas.md, secao 3).
2. O ranking nao roda as duas variantes de 21h; so a chave existe e o padrao e declarado no relatorio.
3. Lista de feriados vem de resumo de busca da REN 1.000/2021; texto primario nao lido (403).

## Notas da primeira rodada (parcialmente superadas pela secao acima)

Pacote `src/mapen_aconselhamento/` (ingest, tarifa, custo, ranking, recomenda, relatorio). BDG2 (custo de predio inteiro): `carregar_bdg2` le o CSV direto do zip; verificado com o medidor `Panther_parking_Lorriane`, 2016-08 (744 horas, 0 ausentes, 8.163,7 kWh, R$ 6.521,63 convencional, R$ 6.361,09 branca). Demonstracao de metodo, nao consumo brasileiro.

## Pontos de atencao e suposicoes

1. `leitura` tem uma 7a coluna `ausente BOOLEAN`, alem das 6 do spec, para carregar a flag de lacuna.
2. `sensor_id` = identificador do predio/andar (ex.: `cu_bems_2018Floor2`); `equipamento_id` = coluna do CU-BEMS sem unidade (ex.: `z2_AC1`; ids de zona se repetem entre andares, o predio e distinguido pelo `sensor_id`). No BDG2, `sensor_id` = nome do medidor e `equipamento_id` = `geral`. `tensao_v` fica NULL (datasets nao tem tensao).
3. Tarifa: so os 4 valores do B3 (convencional, branca ponta/intermediario/fora de ponta) foram convertidos, todos presentes e verificaveis em `docs/regulacao/tarifas_neoenergia_pe.md`. Grupo A, reativo e B1 ficaram fora (nao usados). Tarifas sem tributos e sem bandeira; REH 3.583 nao conferida no PDF da ANEEL (pendencia do doc de regulacao).
4. (superado) Horarios, 21h e feriados: ver a secao da segunda rodada.
5. `config/equipamentos.yaml`: AC flexivel, iluminacao e tomadas nao; fracao movivel 0.18 (faixa 0.10-0.25) e hipotese de cenario com fonte (segunda rodada), nao medicao. Destino fixo: fora de ponta.
6. `.gitignore`: ver item 10 da segunda rodada. `.venv/` e `data/relatorios/` estao ignorados.
7. O zip do BDG2 tem pasta raiz com hash (`buds-lab-...-3d0cbaf/`), entao o caminho `data/meters/cleaned/electricity_cleaned.csv` citado em `docs/datasets_publicos.md` e casado por sufixo.
8. CU-BEMS: custo calculado com kWh = kW x 1/60 h por minuto. Pontos ausentes nao entram no custo (piso). O doc de datasets fala em dados faltantes nos andares 3 e 4; o andar 2 de 2018-08 teve 0,7% de pontos ausentes.
9. `shap` e `pyyaml` adicionados as dependencias; `mypy`, `pandas-stubs`, `types-PyYAML` no extra `dev`. `shap` nao e usado no M1 (so exigido pelo spec).
10. Teste de integracao: sintetico (sempre roda) mais o real do CU-BEMS (pula se faltar `data/publicos`).

## Criterios de aceite

Todos os 7 atendidos: (1) `pip install -e .` e `import mapen_aconselhamento` ok; (2) custo da fixture 24 h dentro de R$ 0,01 (convencional 38,35, branca 39,21, calculo manual no teste); (3) teste da lacuna da reindexacao (a prova vermelha do `defasar` foi retirada junto com a funcao); (4) relatorio real com top-5, custo em R$ e recomendacoes; (5) recomendacao so para `flexivel` (e nao `critico`); (6) disclaimer no relatorio; (7) testes verdes.

## Guard de lag (recriado em 2026-10-01)

`src/mapen_aconselhamento/features.py::adicionar_lags` calcula o lag depois de reindexar ao calendario completo. Teste: `tests/test_features.py`. Prova de vermelho (sem git): trocando `adicionar_lags` por um shift posicional ingenuo, `test_lag_nao_pula_a_lacuna` falha com `AssertionError` (o ingenuo devolve 2.0 em t4 onde o lag correto e NaN); com a implementacao real, 57 testes passam e mypy strict esta limpo.

## Refatoracao em camadas (2026-10-01)

`src/mapen_aconselhamento/` agora segue as mesmas quatro camadas de `src/mapen_plataforma/` (interface > infrastructure > application > domain, dependencias so para dentro). Comportamento inalterado. Os nomes de modulo das secoes acima (ingest, tarifa, custo, ranking, recomenda, relatorio) sao os de antes da refatoracao; o mapa abaixo mostra onde cada um foi parar.

### Mapa de camadas (arquivo -> camada)

| Arquivo | Camada | Dono de |
|---|---|---|
| `domain/tarifa.py` | domain | postos horarios, feriados, preco, vigencia (`Tarifas.de_tabela`) |
| `domain/calendario.py` | domain | reindexacao ao calendario completo, regras de timestamps duplicados |
| `domain/custo.py` | domain | custo por equipamento e faixa |
| `domain/ranking.py` | domain | top-N e % ausente |
| `domain/equipamentos.py` | domain | `Regra`, `ConfigEquipamentos.de_dict` (validacao), cenarios |
| `domain/recomendacao.py` | domain | economia de mover carga entre faixas |
| `domain/features.py` | domain | features de lag sobre calendario completo |
| `application/portas.py` | application | porta `RepositorioLeituras` |
| `application/relatorio_mensal.py` | application | caso de uso `GerarRelatorioMensal` e o resultado `RelatorioMensal` |
| `infrastructure/duckdb_leituras.py` | infrastructure | DDL, insercao, consultas, adaptador `LeiturasDuckDB` |
| `infrastructure/cu_bems.py`, `bdg2.py` | infrastructure | carregadores CU-BEMS e BDG2 |
| `infrastructure/tarifa_csv.py` | infrastructure | leitor do CSV de tarifas (`carregar_tarifas`) |
| `infrastructure/equipamentos_yaml.py` | infrastructure | leitor do YAML (`carregar_config_equipamentos`) |
| `infrastructure/relatorio_arquivo.py` | infrastructure | gravacao do relatorio em disco |
| `infrastructure/caminhos.py` | infrastructure | `RAIZ` e caminhos padrao (antes em `tarifa.py`/`recomenda.py`) |
| `interface/relatorio_markdown.py` | interface | texto do relatorio, ressalvas, `descrever_valores` |
| `interface/cli.py` | interface | entrada de linha de comando (`python -m mapen_aconselhamento.interface.cli`) |

Mudancas de forma, nao de regra: `Tarifas.carregar` virou `infrastructure.tarifa_csv.carregar_tarifas` (leitura do CSV) + `Tarifas.de_tabela` (regras); `ConfigEquipamentos.carregar` virou `carregar_config_equipamentos` + `ConfigEquipamentos.de_dict`; `gerar_relatorio` virou `GerarRelatorioMensal.executar` + `renderizar_relatorio`; `Tarifas.descricao_valores` (texto) foi para a interface como `descrever_valores`. `src/mapen_plataforma` so teve os imports atualizados (`infrastructure/{banco,custo_m1,demo}.py`, `interface/api/composicao.py`).

### Contratos import-linter (`pyproject.toml`, `root_packages` com os dois pacotes)

1. M1 camadas (layers) e M2 camadas (layers).
2. M1 domain/application nao importam `duckdb`, `yaml`, `httpx`, `fastapi`, `starlette` nem `mapen_plataforma`. Pandas e permitido (calculo puro sobre DataFrame). Acesso a relogio nao e coberto pelo import-linter (so imports).
3. M1 inteiro nao importa `mapen_plataforma`.
4. M2 domain/application sem I/O nem framework (ja existia).

Prova de que o contrato morde: copia do `src/` e do `pyproject.toml` em `/private/tmp/mapen_red` (fora do repo, sem git) com dois modulos violadores (`domain/ruim_io.py` importando `duckdb` e `infrastructure.caminhos`; `application/ruim_camada.py` importando `interface.relatorio_markdown`). Saida real do `lint-imports`:

```
M1 camadas: interface > infrastructure > application > domain BROKEN
M1 dominio e aplicacao sem I/O, banco, YAML nem a plataforma BROKEN
M1 nao depende da plataforma KEPT
M2 camadas ... KEPT
M2 dominio e aplicacao sem I/O nem framework KEPT
Contracts: 3 kept, 2 broken.
- mapen_aconselhamento.domain.ruim_io -> mapen_aconselhamento.infrastructure.caminhos (l.2)
- mapen_aconselhamento.application.ruim_camada -> mapen_aconselhamento.interface.relatorio_markdown (l.1)
- mapen_aconselhamento.domain.ruim_io -> duckdb (l.1)
```

No repo real: `Contracts: 5 kept, 0 broken.`

### Antes e depois

| Item | Antes | Depois |
|---|---|---|
| pytest `-W error` | 213 passed | 213 passed |
| Testes M1 | `tests/test_*.py` (6 arquivos) | `tests/m1/{domain,infrastructure,interface}/` (7 arquivos; `test_ingest.py` dividido em `domain/test_calendario.py` e `infrastructure/test_cu_bems_duckdb.py`); mesmas asserções, so imports e chamadas dos leitores/caso de uso mudaram |
| mypy strict | `src` dos dois pacotes + `tests/m2` | + `tests/m1`: `Success: no issues found in 62 source files` |
| import-linter | 2 contratos (so plataforma) | 5 contratos, 2 pacotes |
| Relatorio real CU-BEMS andar 2, 2018-08 | `data/relatorios/cu_bems_2018Floor2_2018-08.md` | regenerado via CLI em `/private/tmp`, `diff` vazio (a linha "Dados" exige `--fonte-dados`; o texto do relatorio antigo era um argumento do chamador) |

Em `test_features.py`, `np.isnan` virou `pd.isna` em duas asserções para o mypy aceitar o escalar de `.loc`; semantica igual.
