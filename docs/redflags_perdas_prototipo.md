# Protótipo de redflags de perdas por área — EPE (UF) + SAMP-Balanço (distribuidora)

**Data:** 2026-08-08 | **Status:** protótipo de análise rodando (sem treino)
**Ferramenta:** `src/redflags_perdas.py` (avulso, ferramenta de dados) + mapa no Desktop
**Contexto:** `modelagem_redflags.md` (abordagem de regressão do esperado) e
`projeto4_neoenergia.md` (desafio Neoenergia PE)

---

## Objetivo

Acionar **redflags por área** quando a perda de energia sair da faixa histórica esperada.
Duas camadas:

1. **UF/mês** — EPE `MERCADO DISTRIBUICAO UF` (2013→2024): `perda_total_GWh` +
   consumo por classe → `perda_rel = perdas/(consumo+perdas)`.
2. **Distribuidora/mês** — ANEEL SAMP-Balanço (2003→2026-06): `Saldo / Perdas na
   Distribuição (valor medido)` em kWh.

Redflag = **z-score sazonal** (por mês do ano, por unidade) acima de 2. Sazonal por mês
porque carga e perdas seguem o calendário (verão/chuva). Só a direção de piora (z>2).

## Resultados — nível UF (sinal primário)

513 observações UF×mês (2006-12→2024-12 — perda_total_GWh existe desde 2006),
**13 redflags históricas**. As mais fortes:

| UF | data | perda_rel | z |
|---|---|---|---|
| BA | 2020-12 | 17,2% | 2,63 |
| ES | 2009-12 | 17,2% | 2,50 |
| CE | 2024-12 | 18,9% | 2,44 |
| RJ | 2024-12 | 29,5% | 2,24 |
| PE | 2020-12 | 20,0% | 2,21 |

**Nível médio 2019+:** Brasil 17,9% | piores: AM 43,7%, AP 43,1%, PA 28,4%, RJ 27,3%
| melhores: PR 7,4%, SC 8,0%, RN 9,3%.

## Foco Neoenergia PE (camada 2 do desafio)

- **Perda_rel PE 2019+ = 18,1%** — 8º/27, acima da média nacional. Perdas altas mas
  estáveis (~17–20% desde 2013), parte da estrutura de custos da distribuidora.
- **1 redflag histórica:** dez/2020 (20,0%, z=2,2) — efeito pandemia (consumo caiu,
  perda física não acompanhou).
- **Tendência recente:** dez/2024 19,2% (z=1,5, quase redflag) — voltando a subir.
- P/ distribuidora (SAMP): NE PE reporta perdas mensais ~550–850 GWh (2024+); sem
  Disponibilidades desde 2024 (ver armadilhas), então a leitura distribuidora fica nas
  **perdas absolutas**.

## Resultados — nível distribuidora

128 distribuidoras, 2003-01→2026-06, 751 redflags (desvios de perda absoluta mensal).
Sinais recentes relevantes:

- **ENEL CE 2026-04:** 1.345 GWh (z=4,1) — salto atípico de perda física.
- **COPEL-DIS 2025-06:** 727 GWh (z=3,7).
- Cuidado: cooperativas pequenas têm séries ruidosas (perda_rel absurda em meses secos) —
  filtrar por porte antes de acionar alerta operacional.

## ARMADILHA IMPORTANTE — EPE ≠ SAMP na definição de "perda"

As duas fontes medem coisas diferentes:

- **EPE `perda_total_GWh`** ≈ perda regulatória (técnica + não-técnica aprovada), ~18%
  do mercado p/ PE.
- **SAMP `Perdas na Distribuição (valor medido)`** ≈ fronteira injetada − entregue aos
  consumidores; inclui outros fluxos (ex.: "Energia Entregue" a outros agentes). P/
  NE PE dá ~35–44% da Disponibilidade — **NÃO comparar diretamente** com a EPE.

Implicação p/ o modelo de redflags: usar **EPE como sinal primário (UF)** e SAMP como
camada exploratória de **perdas absolutas por distribuidora** (desvio mensal), nunca
como porcentagem. (Descoberta registrada — ver também `perdas_energia_brasil.md` §diferença.)

## Saídas

- `data/analise/perdas_uf_mes.csv` — perda_rel por UF/mês.
- `data/analise/redflags_uf.csv` — z-score sazonal + flag por UF/mês.
- `data/analise/redflags_dist.csv` — perda_GWh mensal + z + flag por distribuidora.
- `~/Desktop/brasil_perdas_redflags.png` — mapa: média de perda_rel 2019-24 + nº de
  redflags por UF.

Rodar: `.venv/bin/python src/redflags_perdas.py [--plot] [--uf PE]`

## Limitações / próximos passos

- MMGD (coluna `Einj_MMGD_GWh`) ainda não descontada da série EPE — p/ leitura fina
  recente, subtrair a geração distribuída antes de normalizar.
- Redflag simples (z sazonal). Próximo nível: modelo de regressão do esperado (EPE +
  clima/carga ONS) → resíduo = anomalia, como em `modelagem_redflags.md`.
- 2024+ sem Disponibilidades no SAMP p/ a maioria das distribuidoras (mudança de
  reporte ANEEL) — perdas absolutas continuam; normalização distribuidora fica p/ o
  lote da Neoenergia ou p/ EPE por UF.
- Validar visualmente o mapa (gerado; revisão humana pendente).
