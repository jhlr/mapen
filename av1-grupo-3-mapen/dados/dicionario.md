# Dicionário de dados — AV1 Grupo 3 (MAPEN)

Origem: CU-BEMS, andar 2 (`2018Floor2.csv`), Bangkok, 2018. **Dado real público**, licença CC BY 4.0, https://doi.org/10.6084/m9.figshare.11726517 (o artigo; o arquivo `2018Floor2.csv` tem id 21350166 e cerca de 41 MB). Citação: Pipattanasomporn et al., 2020, *Scientific Data* 7:241. Não é cliente nem medição do MAPEN. A referência calculada é **estimada**.

Recorte: 8 ativos, 09/09/2018 a 01/12/2018 (84 dias; avaliados: 04/11 a 01/12, 28 dias). Ativos: `z1_AC1`, `z1_Light`, `z1_Plug`, `z2_Light`, `z2_Plug`, `z3_Light`, `z4_AC1`, `z4_Plug` (`z4_Plug` fica de propósito: nunca consome, serve de caso de denominador zero).

Recorte de 8 dos 24 equipamentos do andar 2: cobre as quatro zonas (z1 a z4) e os três tipos de carga (ar-condicionado, iluminação e tomadas) e mantém `z4_Plug`, que nunca consome, de propósito, como caso de denominador zero (ver acima). Os outros 16 ficaram fora e o motivo individual da escolha não foi registrado, então os 8 não são uma amostra estatística do andar e os achados não se generalizam para ele.

## Fontes e grãos

| Arquivo | Grão / chave | Registros | Natureza |
|---|---|---|---|
| `dados/recorte_minuto.csv.gz` | 1 linha por minuto; chave `Date` | 120.960 (84 dias × 1.440) | real (extraído do original, sem alteração de valores) |
| `dados/base_diaria.csv` | (`ativo`, `data`) | 672 (8 × 84) | derivada |
| `dados/base_horaria.csv` | (`ativo`, `inicio_hora`) | 16.128 (8 × 84 × 24) | derivada |
| `evidencias/resultados_python.json` | desvio diário por referência A/B/C | 3 × 224 | derivada |

## Campos

| Campo | Significado / tipo | Unidade, domínio, nulos | Papel no cálculo |
|---|---|---|---|
| `Date` | instante do minuto, datetime | 2018-09-09 00:00 a 2018-12-01 23:59, sem duplicados | chave temporal |
| `<ativo>` (no CSV original `<ativo>(kW)`) | potência média no minuto, float | kW, ≥ 0 (0 a 59,61); NaN = minuto sem leitura | entrada de todos os cálculos |
| `kwh` (diária) | energia do dia = média dos minutos presentes (kW) × 24 h | kWh/dia; NaN se o dia tem < 95% dos minutos | **observado** (V1, V2) |
| `minutos_validos` | minutos com leitura no dia | 0 a 1.440 | cobertura |
| `valido` | `minutos_validos` ≥ 1.368 (95%) | booleano | exclui dia da análise (ausência, não zero) |
| `tipo_dia` | `dia_util` (seg-sex) ou `fim_de_semana` | categórico | V3 |
| `expediente` (horária) | hora dentro do horário operacional **assumido**: seg-sex, 07h às 17h59, sem feriados | booleano; **hipótese inferida do perfil de `z1_AC1`, não informada** | contexto da V3 e da seção de sensibilidade |
| `carga_essencial` | carga que precisa permanecer ligada | **não informado** nos 8 ativos (a classificar com o gestor) | ainda não usado; consumo fora do expediente ≠ dispensável |
| `feriado` | 13, 15 e 23/10/2018 | booleano | referência C |
| `kw` (horária) | média dos minutos da hora; NaN se < 45 minutos | kW (potência) | V3 |
| `esperado` | mediana dos `kwh` válidos do **mesmo dia da semana** na janela da referência | kWh/dia | linha de base |
| `desvio` | `kwh − esperado` | kWh/dia, com sinal | V1 (barras), V2 |
| `desvio_rel_pct` | `100 × desvio / esperado`, só se `esperado > 0`; senão vazio (n/c) | % | tabela da V1 |

## Rótulos dos ativos (`dashboard/dados.js`, chave `rotulos`)

Gerados por `rotulos_ativos` em `codigo/av1_desvio.py` a partir do código do CU-BEMS `z<zona>_<tipo><número>`; o código original continua sendo a chave em todos os arquivos.

| Campo | Significado | Exemplo (`z1_AC1`) |
|---|---|---|
| `nome` | tipo por extenso, com o número quando existe | Ar-condicionado 1 |
| `zona` | número da zona do andar | 1 |
| `completo` | `nome · zona N` | Ar-condicionado 1 · zona 1 |
| `tipo` / `descricao` | AC = ar-condicionado, Light = iluminação, Plug = tomadas (*plug loads*) | Ar-condicionado / "Unidade de ar-condicionado da zona." |
| `nota` | só preenchida quando o máximo do recorte é 0 kW | vazio (`z4_Plug` tem a nota) |

Código fora do padrão usa o próprio código como nome. A página `dashboard/nomes.html` mostra esta tabela e os termos do painel.

## Medidas agregadas (V2)

- `soma_positivos` = Σ dos `desvio` > 0 no período (kWh). **Define a ordem.**
- `soma_negativos` = Σ dos `desvio` < 0.
- `saldo` = `soma_positivos + soma_negativos` (permite compensação; não define ordem).

## Referências (janela sempre anterior ao período avaliado)

| ID | Regra | Janela |
|---|---|---|
| A (principal) | mediana de 8 semanas, mesmo dia da semana | 09/09 a 03/11/2018 |
| B | mediana de 4 semanas | 07/10 a 03/11/2018 |
| C | como A, sem os feriados 13, 15 e 23/10 | 09/09 a 03/11/2018 |

kW é potência; kWh é energia. Valores em kWh/dia vêm de potência média × 24 h (a leitura é potência média por minuto, não medidor acumulado).

## Formato de uma linha e mensagem equivalente

Linha real do recorte (`Date`, intervalo de medição de 1 minuto, potência média em kW; colunas do recorte, sem o sufixo do original):

```
Date,z1_AC1,z1_Light,...
2018-11-05 09:00:00,31.25,8.34,...
```

Mensagem equivalente no MAPPEN (esquema da camada de ingestão do repositório, `leitura`): `sensor_id`, `equipamento_id`, `ts` (início do minuto), `potencia_w`, `tensao_v`, `kwh`, `ausente`. O CU-BEMS entra com `potencia_w` = kW × 1000 e `ausente` = minuto sem leitura; o painel desta AV1 lê o CSV direto, sem passar por essa camada.
