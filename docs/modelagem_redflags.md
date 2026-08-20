# Modelagem dos redflags — XGBoost/LightGBM (dados tabulares)

**Data:** 2026-08-08 | **Status:** decisão registrada (a validar com o grupo)
**Contexto:** `perdas_energia_brasil.md` (dados), `consumo_energia_brasil.md`
**Entrada:** EPE (consumo/perdas por UF), SAMP/SAMP-Balanço (mercado por distribuidora),
ONS (carga por subsistema)

---

## 1. Decisão

Para os dados **tabulares** de consumo/distribuição/arrecadação (mês × UF ×
distribuidora × classe), usar **Gradient Boosting — XGBoost ou LightGBM** como modelo
principal de redflags. Árvore de decisão única **não** é recomendada como solução final
(fraca, overfita). A família ensemble é o padrão canônico para dado tabular.

## 2. Por quê (justificativa)

1. **Formato dos dados:** dado tabular heterogêneo — numérico (GWh, kWh, perda %,
   nº clientes) + categórico (UF, distribuidora, classe, modalidade tarifária, mês,
   cativo/livre). Boosting lida com isso sem escalar features nem one-hot pesado.
2. **Não-linearidades e interações:** captura sozinho interações tipo
   "classe residencial × mês de verão × região" sem engenharia manual.
3. **Robustez:** tolera outliers e missing (perdas esparsas em dados antigos), comum
   nesses datasets públicos.
4. **Interpretabilidade:** feature importance + SHAP permitem **justificar cada
   redflag** (ex.: "perda subiu porque X subiu, e o modelo esperava Y") — crítico para
   o cliente aceitar o alerta.
5. **Custo:** treina em minutos no volume atual (SAMP 16,3M linhas) em CPU.

**Sinalização:** se houver GPU e escala > dezenas de milhões de linhas, migrar para
LightGBM com `gpu_use_darts`/hist; senão XGBoost (default). Candidato alternativo de
baseline: Random Forest (mais simples, menos preciso).

## 3. As duas abordagens (aprovadas)

### 3.1 Supervisionado — classificação binária (se houver rótulo)

- **Rótulo:** fraude/anomalia/inspeção confirmada (se o cliente fornecer histórico de
  fiscalizações que acusaram fraude, ou falhas de leitura).
- **Alvo:** `P(anomalia | features)` por área/mês.
- **Features:** perda %, variação de perda, consumo esperado vs real, sazonalidade,
  região, classe, histórico da distribuidora.
- **Limitação atual:** não temos rótulo — depende de dados da Neoenergia ou de
  heurística de "casos confirmados".

### 3.2 Não supervisionado — regressão do esperado, resíduo = anomalia ✅ (pré-requisito)

- **Idéia:** treinar o modelo para **prever a perda esperada** (ou o consumo esperado)
  a partir das features. A diferença `esperado − observado` (resíduo) vira o score de
  anomalia.
- **Redflag:** perda % observada fora da **faixa histórica** daquela área/distribuidora
  (ex.: média 12–15%, mês dá 25% → alerta). Medida por resíduo padronizado ou quantis
  do histórico.
- **Vantagem:** funciona **sem rótulo** — dá para rodar já com EPE + SAMP-Balanço
  (diff distribuída − consumida − perdas por UF/distribuidora, ver `perdas_energia_brasil.md`).
- **Validação:** comparar os redflags gerados contra eventos conhecidos (roubo
  divulgado, relatórios de perda) para calibrar o limiar.

> **Ordem sugerida:** começar pela 3.2 (dados já disponíveis), evoluir para 3.1 quando o
> cliente fornecer rótulos. O resíduo da 3.2 pode virar feature/rótulo fraco da 3.1.

## 4. Stack e passos

1. Baseline de correlação/heurística (perda % e desvio vs histórico) em `src/`.
2. Modelo 3.2 com LightGBM/XGBoost (validação temporal — nunca embaralhar mês).
3. SHAP por redflag p/ explicabilidade.
4. Evolução para 3.1 com rótulos do cliente (Kickoff/SR1).

## 5. Referências cruzadas

- Dados: `perdas_energia_brasil.md` (§2 EPE, §3 SAMP-Balanço).
- Dataset SAMP: `origem_dos_dados.md` §12–14.
- Subprojeto CV (fotos/leitura): `plano_subprojeto_cv.md` (redflag de perda →
  priorizar fiscalização de fotos na área).
