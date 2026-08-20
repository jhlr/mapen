### 1. Chaymaa/grdf-* — GÁS (fora do foco, baixado a pedido)
- **URLs:** padrão `https://huggingface.co/datasets/Chaymaa/<nome>` para as 8 variantes:
  `grdf-v0`, `grdf-v1`, `GRDF_donut`, `GRDF-aug-donut`, `grdf-inference`,
  `grdf-rotationAug1`, `grdf-inference-aug-iter2-v2`, `grdf-inferenceC`
  (em `data/grdf-*/`).
- **Conteúdo:** medidores de **gás** (GRDF — Gaz Réseau Distribution France), 25–697 imgs.
- **Falharam** (aguardando janela do CDN xet): `grdf-rotationAug1`,
  `grdf-inference-aug-iter1`, `grdf-inference-aug-iter2`.
- **Download:** `HF_HUB_DISABLE_XET=1 .venv/bin/hf download Chaymaa/<nome> --repo-type dataset`
  → copiar para `data/<nome>/`.

### 2. ud-smart-city/water-meter-image — ÁGUA (re-baixando)
- **URL:** https://huggingface.co/datasets/ud-smart-city/water-meter-image
- **Licença:** CC BY-NC-ND 4.0 | **Conteúdo:** 60 imagens de hidrômetro + `water meters.csv`
  (`images/` no repo; flat em `data/ud_smart_city_water/`).
- **Status:** primeiro download veio incompleto (só 20/60 imagens) — re-baixando em
  background (job em `/tmp/ud_water_dl.log`). Conferir contra o repo (63 = 63).
- **Download:** `HF_HUB_DISABLE_XET=1 .venv/bin/hf download ud-smart-city/water-meter-image --repo-type dataset --local-dir data/ud_smart_city_water`

### 3. Power grid maps (BR + internacional)
- **URLs:** https://dados.ons.org.br (datasets `linha-transmissao`, `subestacao`,
  `capacidade-transformacao`) e Zenodo `10.5281/zenodo.14873694` (Omã/Nigéria).
- **Ver** `power_grid_maps.md` (URLs S3 e instruções). ONS (SUBESTACAO/
  LINHA_TRANSMISSAO/CAPACIDADE_TRANSFORMACAO) em `data/power_grid_maps/ons_brasil/`;
  Zenodo em `data/power_grid_maps/zenodo/`.

### 4. Consumo/carga ONS (geo + temporal)
- **URLs:** https://dados.ons.org.br — datasets `curva-carga`, `carga-energia`,
  `carga-mensal`, `balanco-energia-subsistema`, `demanda_maxima_di`, `cargaglobal-roraima`.
- **Ver** `consumo_energia_brasil.md`. Séries horárias/diárias/mensais por subsistema
  (2000→2026) em `data/consumo/ons/`, baixadas via:
  `.venv/bin/python src/ons_load.py <dataset> [--ano YYYY]`

### 5. SAMP/ANEEL — mercado por distribuidora
- **URL:** https://dadosabertos.aneel.gov.br/dataset/samp
- **Licença:** ODbL | **Conteúdo:** consumo faturado mensal por distribuidora
  (129 agentes), classe/subclasse, modalidade/subgrupo tarifário, posto, cativo/livre.
- **Granularidade:** distribuidora + `IdeNucleoCeg` (núcleo de medição, ex.: 246 na
  CEMIG, 180 na CELESC) — menor que UF, maior que município.
- **Período:** 2003-01 → 2026-06, mensal. 24 parquets ≈ 170MB em `data/consumo/samp/`
  (16,3M linhas). Download direto do CKAN da ANEEL (CSV/parquet por ano).
- **Ver** `consumo_energia_brasil.md` §7.

### 6. EPE — Consumo Mensal (UF) e Mercado de Distribuição (perdas por UF)
- **URLs:** https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-consumo-mensal-de-energia-eletrica
  | https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-mercado-de-distribuicao
- **Licença:** dados públicos EPE | **Conteúdo:** consumo (MWh) e nº consumidores por
  UF × sistema × classe × cativo/livre (2004→2026-05); mercado com `Consumo_GWh`,
  `Einj_MMGD_GWh` e `perda_total_GWh` por UF (~2004→2024-12).
- **Formato:** xlsx (13,7 MB + 628 KB) em `data/consumo/epe/`. Planilhas `... UF` são
  as de nível UF.
- **Ver** `perdas_energia_brasil.md` §1-2.

### 7. ANEEL — SAMP-Balanço (energia injetada vs vendida por distribuidora)
- **URL:** https://dadosabertos.aneel.gov.br/dataset/samp-balanco
- **Licença:** ODbL | **Conteúdo:** `Disponibilidades` (Energia Recebida/Injetada Total)
  e `Requisitos` (Energia Vendida) em kWh por distribuidora, mensal 2003→2026-06
  (545k linhas, 164 agentes). Perda = Disponibilidades − Requisitos.
- **Arquivo:** `data/consumo/samp_balanco/samp-balanco.parquet` (3,8 MB) + dicionário.
- **Ver** `perdas_energia_brasil.md` §3.

### 8. Malha UF IBGE (`data/br_ufs.json`) — geo administrativo
Baixado em 2026-08-08 (pendência de documentação) via API de malhas do IBGE:
`https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF`
(27 UFs, polígonos/`codarea`). Usado como base geo p/ ancorar mapas (rede, consumo,
perdas). Fonte única de geometria UF no projeto — NÃO usar `br.geojson` de contorno
BR (1 feature só, sem UFs).

---

## Notas de troubleshooting

- **CDN xet do HF instável:** downloads grandes falhando com
  `RuntimeError: File reconstruction error: CAS Client Error: ... Request middleware error`
  (o CDN `xorbs/xet` está com problemas; **não é a rede local**). Mitigações:
  re-tentar com intervalos, 1 arquivo por vez, menos concorrência.
- **`HF_HUB_DISABLE_XET=1`** resolveu o travamento do UFPR-AMR (`.incomplete` de 0 bytes
  em toda tentativa → concluído em ~10 min). Usar em downloads grandes no HF.
- **`hf download`** (huggingface_hub) tem resume/retry nativo e lida melhor com o xet —
  preferir para arquivos grandes; `curl` para S3/parquet de fonte direta.
- **Download sempre em background sem timeout** (`nohup ... &` + log) — ver AGENTS.md global.
- **Datasets que exigem conta/chave/licença** (Roboflow, UFPR-ADMR-v2, NRC-GAMMA,
  Pointer-10K, SCUT-WMN, WMeter5K, Suez): ver `candidatos_nao_baixados.md` no projeto
  `leiturista`.

---

## Docs irmãos

| Doc | Conteúdo |
|---|---|
| `consumo_energia_brasil.md` | Datasets de consumo de energia BR (geo+temporal): ONS, EPE, CCEE, ANEEL, PyPSA-Brasil |
| `perdas_energia_brasil.md` | Perdas de energia por área (UF/distribuidora): EPE, SAMP-Balanço, PARA/Luz na Tarifa, metodologia MAPEN |
| `power_grid_maps.md` | Mapas de rede: ONS (SIN), Zenodo Omã/Nigéria, SIGEL/EPE não baixados |
| `modelagem_redflags.md` | Escolha XGBoost/LightGBM + 2 abordagens de redflag (tabulares) |
| `contexto_mapen.md` | Contexto geral do projeto MAPEN |

> Docs de CV (artigos, projetos_notaveis, candidatos_nao_baixados, copel_amr,
> finetune_trocr, plano_subprojeto_cv, projeto4_neoenergia, …) → projeto `leiturista`.
