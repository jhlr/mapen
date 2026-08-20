# Perdas de energia elétrica no Brasil — fontes de dados

Data: 2026-08-08. Foco MAPEN: **energia distribuída vs consumida por área** →
perda ≈ distribuída − consumida, e redflags por região/UF/distribuidora.

## Resumo do que existe (medido, baixável)

| Nível geo | Distribuída | Consumida | Perda | Fonte |
|---|---|---|---|---|
| **UF/mês** | `Einj_MMGD_GWh` | `Consumo_GWh` | **`perda_total_GWh`** | EPE Mercado de Distribuição (planilha `MERCADO DISTRIBUICAO UF`) |
| **UF/mês** | — | `Consumo` (kWh/GWh) | — | EPE Consumo Mensal (planilha `CONSUMO E NUMCONS SAM UF`) |
| **distribuidora/mês** | `Disponibilidades` (injetada) | `Requisitos` (vendida) | Saldo = injetada − vendida | ANEEL SAMP-Balanço |
| **distribuidora/mês** | — | `VlrMercado` (kWh) | — | ANEEL SAMP |

## 1. EPE — Mercado de Distribuição (perdas por UF)

- **Arquivo:** `data/consumo/epe/mercado_distribuicao.xlsx` (628 KB)
- **URL:** https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-mercado-de-distribuicao
- **Planilha-chave:** `MERCADO DISTRIBUICAO UF`
- **Colunas:** `Data, Regiao, Sistema, UF, Classe, TipoConsumidor, TipoValor,
  Consumo_GWh, Einj_MMGD_GWh, perda_total_GWh, DataVersao`
- **Granularidade:** UF × classe × cativo/livre, mensal (~2004 → 2024-12).
- **Conteúdo:** consumo faturado, energia injetada de MMGD e **perda total por UF**.
  É a única fonte pública de perdas em nível de UF.
- **Licença:** dados públicos EPE.
- Nota: planilha `MERCADO DISTRIBUICAO` (região/subsistema) é mais grossa — usar a UF.

## 2. EPE — Consumo Mensal (consumo por UF)

- **Arquivo:** `data/consumo/epe/consumo_mensal.xlsx` (13,7 MB)
- **URL:** https://www.epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-consumo-mensal-de-energia-eletrica
- **Planilha-chave:** `CONSUMO E NUMCONS SAM UF`
- **Colunas:** `Data, DataExcel, UF, Regiao, Sistema, Classe, TipoConsumidor,
  Consumo, Consumidores, DataVersao`
- **Granularidade:** UF × sistema × classe × cativo/livre, mensal (2004-01 → 2026-05),
  60.652 linhas.
- **Conteúdo:** consumo (MWh) e nº de consumidores. Mesma base SAM da ANEEL.
- **Licença:** dados públicos EPE.
- Outras planilhas: consumo por região/subsistema, setor industrial (RG/UF),
  séries históricas BEN 1970-1989 e Eletrobras 1990-2003.

## 3. ANEEL — SAMP-Balanço (energia injetada vs vendida por distribuidora)

- **Arquivo:** `data/consumo/samp_balanco/samp-balanco.parquet` (3,8 MB) +
  `dd-samp-balanco.pdf` (dicionário)
- **URL:** https://dadosabertos.aneel.gov.br/dataset/samp-balanco (também CSV 135 MB)
- **Colunas:** `DatGeracaoConjuntoDados, NumCPFCNPJ, NomAgente, AnmCompetenciaBalanco
  (YYYYMM), DscModalidadeBalanco, DscFluxoEnergia, DscCctBalanco, DscClassificacaoAgente,
  AnoReferenciaBalanco, MesReferenciaBalanco, DscDetalheBalanco, VlrEnergia (kWh)`
- **Granularidade:** distribuidora (~164 agentes), mensal, 2003-01 → 2026-06
  (545.340 linhas).
- **Conteúdo:** `DscCctBalanco` em `Disponibilidades` (Energia Recebida / Injetada Total),
  `Requisitos` (Energia Vendida — cativo/livre) e `Saldo`. **Perda por distribuidora =
  Disponibilidades − Requisitos.**
- **ARMADILHA (2026-08, verificado no protótipo `redflags_perdas_prototipo.md`):** a
  métrica oficial ANEEL no parquet é `Saldo / Perdas na Distribuição (valor medido)`
  (2003→2026-06). O NÚMERO dela ≠ perda regulatória da EPE (p/ Neoenergia PE: ~35–44%
  da Disponibilidade vs ~18% no EPE — o SAMP "valor medido" é fronteira − entregue,
  inclui outros fluxos). E **desde 2024 a maioria das distribuidoras NÃO reporta mais
  Disponibilidades/Requisitos** no SAMP-Balanço (só o Saldo) — p/ 2024+ a normalização
  distribuidora não é possível sem outra fonte. Não comparar diretamente EPE vs SAMP.
- **Licença:** ODbL.

## 4. ANEEL — SAMP (consumo por distribuidora)

- **Arquivo:** `data/consumo/samp/*.parquet` (24 parquets, 2003→2026, 16,3M linhas)
- **URL:** https://dadosabertos.aneel.gov.br/dataset/samp
- Consumo faturado mensal por distribuidora/classe/subgrupo tarifário, com
  `IdeNucleoCeg` (núcleo de medição, recorte ≤ concessionária). Detalhes em
  `consumo_energia_brasil.md` §7.

## 5. PARA / Luz na Tarifa (ANEEL) — só visual

- **Portal:** https://portalrelatorios.aneel.gov.br/luznatarifa (Power BI embed)
- Relatórios pertinentes (granularidade: distribuidora):
  - **Mercado Cativo - SAMP**: UC + mercado (MWh) + receita + receita c/ tributos,
    por distribuidora/classe/subgrupo, 2003→.
  - **Relatório de Perdas de Energia**: perda não-técnica real vs regulatória (BT),
    perdas totais/energia injetada, base de perdas dos processos tarifários.
    Histórico perdas não-técnicas desde 2008; processos tarifários desde 2013.
  - **Base de Dados das Tarifas**: TUSD + TE e componentes, 2010→.
- **Extração:** cada página embute `EMBED_ACCESS_TOKEN` (exp ~24h); é possível
  extrair via automação de browser (Playwright + `powerbi-client`, `visual.getData()`).
  **Não há API REST pública de download.**
- PDF homólogo do Relatório de Perdas: https://git.aneel.gov.br/publico/centralconteudo/-/raw/main/relatorioseindicadores/tarifaeconomico/Relatorio_Perdas_Energia.pdf
  (Cloudflare bloqueia curl; abre no browser).

## 6. Outros dados abertos ANEEL (secundários)

- DEC/FEC coletivos por conjunto/distribuidora/UF (2000–2029): `indicadores-coletivos-de-continuidade-dec-e-fec`
- INDGER (comerciais/serviços por distribuidora): `indger-indicadores-gerenciais-da-distribuicao`
- Inadimplência mensal por distribuidora: `indqual-inadimplencia`
- Interrupções (todas as ocorrências): `interrupcoes-de-energia-eletrica-nas-redes-de-distribuicao`
- Chave município↔distribuidora (qualidade): `indqual-municipio`
- Rede geo da distribuidora (ArcGIS): BDGD — https://dadosabertos-aneel.opendata.arcgis.com

## 7. O que NÃO existe (não procurar de novo)

1. **Consumo/mercado/receita/perdas por município** — máximo público é distribuidora
   (SAMP/SAMP-Balanço) ou UF (EPE). Município só para indicadores de **qualidade**
   (DEC/FEC via `indqual-municipio`).
2. **Perdas por núcleo/área** dentro da distribuidora.
3. **Perdas no Anuário Estatístico EPE e no BEN** — perdas só em nível nacional (BEN);
   Anuário não tem tabela de perdas.
4. CCEE por UF: portal dá 403 em fetch automático; mirror Kaggle
   (`danielluzzi/ccee-brazil-energy-consumption`) cobre só 2018-2020 com licença
   não declarada — o EPE passa por cima e não vale o risco.

## Metodologia sugerida (MAPEN)

1. Por **UF/mês**: `perda_total_GWh` direto do EPE Mercado de Distribuição UF →
   redflag quando perda normalizada (perda/consumo) sobe fora da faixa histórica.
2. Por **distribuidora/mês**: SAMP-Balanço `Disponibilidades − Requisitos` → perda
   por concessionária; cruzar com SAMP (mercado) e `IdeNucleoCeg` para granularidade
   sub-concessionária.
3. MMGD entra como injetada (`Einj_MMGD_GWh`) — não esquecer ao comparar com ONS
   (carga do SIN é bruta).
