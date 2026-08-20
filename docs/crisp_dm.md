# Estado do projeto no CRISP-DM

**Data:** 2026-08-12 | **Status:** seguindo CRISP-DM de facto, sem artefato formal até hoje
**Método:** CRISP-DM clássico (6 fases), ver `docs/contexto_mapen.md` (contexto)
**Como ler:** ✅ feito | 🔶 parcial | ⬜ não iniciado — checklist de saída adaptado ao MAPEN

---

## Mapa de fases

| Fase | Estado | O que existe | Lacuna |
|---|---|---|---|
| 1. Entendimento do negócio | 🔶 | `contexto_mapen.md` (problema, solução, escopo, stakeholders: disciplina + Neoenergia) | **Sem critérios de sucesso mensuráveis** |
| 2. Entendimento dos dados | ✅ | `origem_dos_dados.md`, `consumo_energia_brasil.md`, `power_grid_maps.md`, `perdas_energia_brasil.md`; dados baixados (EPE, SAMP, SAMP-Balanço, ONS, IBGE, grid maps); armadilha EPE≠SAMP descoberta | descrição de variáveis consolidada (parcial) |
| 3. Preparação dos dados | 🔶 | parquet flat por dataset; `perda_rel`, z-score sazonal derivados (`data/analise/*.csv`) | dataset final formalizado + doc de derivação completa; **checagem de leakage** |
| 4. Modelagem | 🔶 | `modelagem_redflags.md` (decisão XGBoost/LightGBM, 2 abordagens, stack) + baseline heurística z-sazonal (`src/redflags_perdas.py`) | **modelo 3.2 (regressão do esperado) não treinado** |
| 5. Avaliação | 🔶 | redflags históricas geradas (13 UF, 751 distribuidora); armadilhas documentadas | **validação contra eventos conhecidos** pendente; revisão do processo formal |
| 6. Implantação | ⬜ | saídas em CSV/PNG (`data/analise/`, Desktop) | aceitação, plano de deploy/monitoramento, relatório final |

---

## 1. Entendimento do negócio

**Entregável:** objetivos, critérios de sucesso (financeiros + técnicos), aceitação, plano de projeto.

- ✅ Problema: perdas de distribuição, impacto financeiro/operacional, identificar **onde** e **quanto** (`contexto_mapen.md` §Problema).
- ✅ Solução: comparar distribuída vs consumida → perda → criticidade por região → indicadores financeiros (redflags por área).
- ✅ Stakeholders: disciplina BD2026.1 (Grupo 3) + desafio Neoenergia PE (Projeto 4).
- ✅ Escopo: energia elétrica; geo máximo UF (subsistema ONS / UF CCEE / município modelado).

### ⬜ Critérios de sucesso (FALTA — definir com o grupo)

| Critério | Sugestão MAPEN |
|---|---|
| Financeiro | R$ de perda "explicada"/priorizada por redflag, ou nº de fiscalizações direcionadas |
| Técnico (recall) | % das redflags acionadas que coincidem com evento real conhecido (ex.: 13 redflags UF) |
| Técnico (precisão) | % de alertas confirmados (falsos positivos controlados) |
| Aceitação | decisão por redflag justificável por SHAP/feature importance (modelagem 3.2) |

## 2. Entendimento dos dados

- ✅ Fontes mapeadas e **origem documentada** antes do download (`origem_dos_dados.md`).
- ✅ Séries geo+temporais: ONS subsistema (horária 2000→2026), EPE UF/mês, SAMP e SAMP-Balanço distribuidora/mês, malha UF IBGE, mapas de rede.
- ✅ Qualidade: armadilha **EPE ≠ SAMP** na definição de "perda" descoberta e documentada (`redflags_perdas_prototipo.md` §ARMADILHA) → decisão de usar EPE como sinal primário e SAMP como perdas absolutas.
- ✅ Limitações: bairro inexistente (LGPD/comercial), CCEE 403, MMGD não descontada, SAMP sem Disponibilidades 2024+, perdas só nacionais no BEN.
- 🔶 Descrição de variáveis consolidada num único doc (está espalhada).

## 3. Preparação dos dados

- ✅ Datasets em parquet flat, 1 pasta por dataset (`data/consumo/ons|epe|samp|samp_balanco`).
- ✅ Derivações: `perda_rel = perdas/(consumo+perdas)`, z-score sazonal por mês/unidade (`data/analise/perdas_uf_mes.csv`, `redflags_uf.csv`, `redflags_dist.csv`).
- 🔶 Dataset final "modelo-ready" (features + target para a 3.2) não consolidado num arquivo único documentado.
- ⬜ **Checagem de leakage** (validação temporal, sem embaralhar mês — decidido em `modelagem_redflags.md` §4, mas não verificado no pipeline).

## 4. Modelagem

- ✅ Decisão técnica registrada: Gradient Boosting (XGBoost/LightGBM) p/ dado tabular; justificativa completa (heterogeneidade, interações, robustez, SHAP, custo).
- ✅ Duas abordagens: 3.1 supervisionado (sem rótulo hoje) / 3.2 não supervisionado (regressão do esperado → resíduo = anomalia). **Ordem: 3.2 primeiro** (dados já disponíveis).
- ✅ Baseline heurística rodando: z-score sazonal por UF e distribuidora (513 obs UF, 13 redflags; 128 distribuidoras, 751 redflags).
- 🔶 Próximo passo da stack (baseline → LightGBM/XGBoost com validação temporal → SHAP) **não executado**.

## 5. Avaliação

- 🔶 Redflags históricas geradas (BA 2020-12, ENEL CE 2026-04 z=4,1, COPEL-DIS 2025-06, etc.) — candidatas a **validação contra eventos conhecidos** (roubos divulgados, relatórios de perda).
- 🔶 Revisão do processo informal (armadilhas e limitações documentadas ao longo do caminho).
- ⬜ Comparação contra critérios de sucesso (que ainda não existem) e decisão seguir/voltar formal.

## 6. Implantação

- ⬜ Nada feito (esperado nesta fase do projeto). Saídas atuais: CSV em `data/analise/` + PNG no Desktop.
- Definir no final: plano de deploy (script/pipeline reproduzível), monitoramento (drift), teste de aceitação, relatório final.

---

## Próximos passos sugeridos (ordem)

1. Definir critérios de sucesso (fase 1) — fecha a maior lacuna.
2. Consolidar dataset final da 3.2 + doc de derivação e checagem de leakage (fase 3).
3. Treinar baseline 3.2 (regressão do esperado) com validação temporal (fase 4).
4. Validar as 13 redflags UF contra eventos conhecidos (fase 5).
