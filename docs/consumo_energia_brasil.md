# Consumo de energia elétrica no Brasil — datasets (geo + temporal)

**Levantamento:** 2026-08-08. Objetivo: séries de **consumo** de energia elétrica no
Brasil com dimensão **geográfica** (subsistema/região/UF/município) e **temporal**
(hora/dia/mês/ano) para treinar modelo de previsão / análise espacial.

Granularidade geo possível em fontes públicas BR: **subsistema ONS (4)** > **região** >
**UF/estado** > **município (5.570)**. Consumo faturado por município NÃO é publicado
como dado aberto (as distribuidoras não liberam); município só via proxy (PyPSA-Brasil).

---

## 1. ONS Dados Abertos — série oficial de carga (fonte primária) ✅ baixando

- **Portal:** https://dados.ons.org.br | **API CKAN:** `https://dados.ons.org.br/api/3/action/package_search?q=carga`
- **Licença:** Creative Commons Atribuição (CC BY)
- **Formato:** CSV / XLSX / **PARQUET** / JSON (arquivos por ano)
- **S3:** `https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/{dataset}/{ARQUIVO}`
- **Origem dos dados:** carga verificada pelo ONS junto às usinas/medição do SIN
  (sistema de operação em tempo real); geo = **subsistema** (SE/CO, S, NE, N).

### Dataset `curva-carga` — Curva de Carga Horária ✅ schema verificado
- **Granularidade temporal:** horária (todos os 8.760 h do ano), 2000→2026 (27 arquivos)
- **Geo:** 4 subsistemas
- **Colunas (verificado no parquet de 2026):** `id_subsistema` (N/NE/S/SE),
  `nom_subsistema` (NORTE/NORDESTE/SUL/SUDESTE/CENTRO-OESTE), `din_instante` (datetime
  horário), `val_cargaenergiahomwmed` (carga média horária, MWmed)
- **Tamanho:** ~2 MB/ano (total ~55 MB em parquet); 20928 linhas/ano (4 subsistemas × 8.736 h)
- **Exemplo:** `('SE', 'SUDESTE/CENTRO-OESTE', 2026-01-01 00:00, 43423.5)`

### Dataset `balanco-energia-subsistema` — Balanço de Energia nos Subsistemas
- **Temporal:** horária, 2000→2026 | **Geo:** 4 subsistemas
- **Conteúdo:** carga + **oferta** desagregada por geração (hidro, térmica, eólica,
  fotovoltaica) em MWmed — permite comparar consumo vs. geração por região/hora.

### Dataset `carga-energia` — Carga de Energia Diária
- **Temporal:** diária, 2000→2026 | **Geo:** subsistema
- Carga verificada diária (base para o histórico diário).

### Dataset `carga-mensal` — Carga de Energia Mensal
- **Temporal:** mensal | **Geo:** subsistema (arquivo único, `CargaMensal.parquet`)

### Dataset `demanda_maxima_di` — Demanda Máxima Diária por Subsistema
- **Temporal:** diária, 2024→2026 | **Geo:** subsistema
- Inclui o valor **estimado da micro e minigeração distribuída (MMGD)** com base em
  dados meteorológicos previstos — útil para corrigir o "consumo real" do SIN.

### Dataset `cargaglobal-roraima` — Roraima (sistema isolado)
- Carga global de Roraima (não interligado ao SIN até 2023; útil p/ cobertura total).

### Outros relacionados (programação, não consumo verificado)
`carga-energia-programada`, `carga-energia-verificada` (previsão vs. realizado).

**Como baixar:** script reutilizável `src/ons_load.py` (API CKAN + curl S3, skip de
arquivos já baixados). Ex.:
```
.venv/bin/python src/ons_load.py curva-carga               # todos os anos
.venv/bin/python src/ons_load.py curva-carga --ano 2026     # só um ano
```
Destino: `data/consumo/ons/<dataset_id>/<ARQUIVO>.parquet`

---

## 2. EPE — Consumo Mensal de Energia Elétrica por Classe (regiões e subsistemas)

- **URL:** https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/consumo-de-energia-eletrica
- **Origem dos dados:** EPE consolida o faturamento das distribuidoras por **classe**
  de consumo (Residencial, Industrial, Comercial, Rural, Poder Público, Iluminação
  Pública, Serviço Público) × **região/subSistema** — série longa (desde ~1979).
- **Geo:** região e subsistema | **Temporal:** mensal
- **Formato:** planilhas (xls) por ano na página de dados abertos da EPE.
- **Licença:** CC BY. **Ainda não baixado.**

---

## 3. CCEE — Mercado de Energia (consumo por estado/subsistema)

- **URL:** https://www.ccee.org.br (área de dados de mercado; `ccee.org.br/mercado` dá **403** em fetch automático)
- **Origem dos dados:** CCEE (Câmara de Comercialização) mede o **consumo de mercado**
  dos agentes (a carga comercializada), granularidade **UF/estado e subsistema**, mensal.
- **Formato:** planilhas xls de séries consolidadas. Requer navegação manual no portal.
- **Licença:** pública, uso acadêmico comum. **Ainda não baixado.**

---

## 4. ANEEL — mercado por concessionária e geo de empreendimentos

- **Mercado/consumo:** a ANEEL publica relatórios de mercado por **concessionária** e UF
  (não por município). Dados no portal de dados abertos da ANEEL.
- **SIGEL** (`sigel.aneel.gov.br`): shapefiles georreferenciados de **geração,
  transmissão, subestações e área de concessão** das distribuidoras — geo de
  infraestrutura (não consumo). Já citado em `power_grid_maps.md`.

---

## 5. PyPSA-Brasil — load profiles por UF (27)

- **URL:** https://github.com/pypsa-brasil/pypsa-brasil
- **Origem dos dados:** modelo de sistemas de energia de código aberto. Os **load
  profiles são por estado/UF (27)**, não por município — a decomposição do paper vai de
  ONS (subsistema) → estado, ponderando vazões/capacidade hidro instalada por estado.
  A afirmação anterior de "por município (~5.570)" estava **errada** (corrigida em
  2026-08-08).
- **Observação:** fetch do GitHub retornou 404 em 2026-08-08 (repo pode ter sido
  renomeado/privatizado) — **confirmar antes de usar**.
- Alternativa com geografia municipal + geoespacial: ver paper *Geospatial Mapping of
  Large-Scale Electric Power Grids* (`power_grid_maps.md`, Zenodo Omã/Nigéria).

---

## 6. Mirror no Hugging Face (pré-empacotado)

- **`SamuelM0422/Hourly-Electricity-Demand-Brazil-Dataset`** (https://huggingface.co/datasets/SamuelM0422/Hourly-Electricity-Demand-Brazil-Dataset)
- Espelho da **Curva de Carga Horária do ONS (2000–2025)**, 2.31 MB, csv/xlsx/parquet,
  colunas: data/hora + carga total do SIN + carga por subsistema.
- Já existe **modelo treinado** na família: `SamuelM0422/PatchTST-Hourly-Electricity-Demand-Brazil`
  (forecasting, 138k downloads) — sinaliza **angulo de artigo/produto** (baseline
  comparável + ganho com geo/demografia).

---

## 7. SAMP/ANEEL — mercado por distribuidora (2003→2026)

- **URL:** https://dadosabertos.aneel.gov.br/dataset/samp
- **Origem:** declarado pelas concessionárias/permissionárias de distribuição à ANEEL
  (Resolução Normativa ANEEL nº 1.003/2022). É o consumo **faturado** (mercado), o que
  casa com o pilar "consumido" do MAPEN.
- **Granularidade:** distribuidora (~65) — **menor que UF, maior que município**. Campo
  `IdeNucleoCeg` = núcleo de medição (recorte geográfico menor dentro da concessionária),
  caminho para um nível mais fino. Inclui **todas as distribuidoras**, inclusive o grupo
  Neoenergia (Coelba/BA, CELPE/PE, Cosern/RN, Elektro/SP+MS, Neoenergia Brasília/DF).
- **Temporal:** mensal, 2003 em diante (24 parquets ≈ 170MB).
- **Dimensões:** classe/subclasse de consumo, modalidade/subgrupo tarifário, posto,
  opção de energia (cativo/livre), CNPJ do agente.
- **Licença:** ODbL (Open Data Commons).
- **Nota:** consumo em kWh (`VlrMercado`); também há `num-consumidores` e
  `mercado-livre` correlatos no portal da ANEEL.

---

## 8. EPE — Consumo Mensal por UF + Mercado de Distribuição (perdas)

- **URLs:** https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-consumo-mensal-de-energia-eletrica
  e https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-mercado-de-distribuicao
- **Arquivos:** `data/consumo/epe/consumo_mensal.xlsx` (13,7 MB) e
  `data/consumo/epe/mercado_distribuicao.xlsx` (628 KB)
- **Consumo mensal (planilha `CONSUMO E NUMCONS SAM UF`):** consumo (MWh) + nº de
  consumidores por UF × sistema × classe × cativo/livre, 2004-01 → 2026-05.
- **Mercado de distribuição (planilha `MERCADO DISTRIBUICAO UF`):** `Consumo_GWh`,
  `Einj_MMGD_GWh` e **`perda_total_GWh`** por UF × classe × cativo/livre
  (~2004 → 2024-12). Fonte de perdas por UF.
- **Licença:** dados públicos EPE. Ver `perdas_energia_brasil.md` §1-2.

---

## Comparativo

| Fonte | Geo | Temporal | Período | Formato | Licença | Status |
|---|---|---|---|---|---|---|
| ONS `curva-carga` | subsistema (4) | horária | 2000–2026 | parquet/csv/xlsx | CC BY | ✅ baixando |
| ONS `balanco-energia-subsistema` | subsistema (4) | horária | 2000–2026 | parquet/csv/xlsx | CC BY | ✅ baixando |
| ONS `carga-energia` (diária) | subsistema | diária | 2000–2026 | parquet/csv/xlsx | CC BY | ✅ baixando |
| ONS `carga-mensal` | subsistema | mensal | histórico | parquet/csv/xlsx | CC BY | ✅ baixando |
| ONS `demanda_maxima_di` | subsistema | diária | 2024–2026 | parquet/csv/xlsx | CC BY | ✅ baixando |
| ONS `cargaglobal-roraima` | Roraima | vários | histórico | parquet/csv/xlsx | CC BY | ✅ baixando |
| EPE consumo por classe | região/subsistema | mensal | ~1979→ | xls | CC BY | ⏳ não baixado |
| CCEE mercado | UF/subsistema | mensal | histórico | xls | pública | ⏳ não baixado |
| ANEEL mercado | concessionária/UF | mensal | histórico | — | pública | ⏳ não baixado |
| **SAMP/ANEEL** | **distribuidora (≤UF)** | mensal | 2003–2026 | parquet/csv | ODbL | ✅ baixado (24 parquets) |
| **SAMP-Balanço/ANEEL** | **distribuidora** (injetada vs vendida) | mensal | 2003–2026 | parquet/csv | ODbL | ✅ baixado |
| **EPE consumo mensal (UF)** | **UF** × classe × cativo/livre | mensal | 2004–2026 | xlsx | pública | ✅ baixado |
| **EPE mercado distribuição (UF)** | **UF** × classe | mensal | ~2004–2024 | xlsx | pública | ✅ baixado (inclui `perda_total_GWh`) |
| PyPSA-Brasil loads | **UF (27)** | horária | 2019 | parquet/csv | MIT | ⚠️ 404, confirmar |
| HF `SamuelM0422/Hourly-Electricity-Demand` | subsistema | horária | 2000–2025 | parquet/csv | ? | ⏳ não baixado |

## Observações / próximos passos

1. ONS = **carga (SIN)**, não consumo faturado — para "consumo" estrito, cruzar com
   EPE/CCEE (que usam faturamento das distribuidoras).
2. Geografia fina: distribuidora (SAMP, ≤UF) → UF (EPE) → subsistema (ONS). Município
   só via `IdeNucleoCeg` do SAMP (núcleo de medição, menor que a concessionária) ou
   modelado (PyPSA-Brasil). **Bairro/setor censitário não existe público**.
3. **Perdas por área**: `perda_total_GWh` por UF (EPE Mercado de Distribuição) e
   `Disponibilidades − Requisitos` por distribuidora (SAMP-Balanço) — ver
   `perdas_energia_brasil.md`.
4. Ângulo empacotável: dataset BR unificado consumo+carga por subsistema, atualizado
   (ONS publica até o ano corrente) — gap claro vs. mirrors do HF (2000–2025).
5. Dicionários de dados ONS: `DicionarioDados_*.pdf` no mesmo bucket S3 de cada dataset.
