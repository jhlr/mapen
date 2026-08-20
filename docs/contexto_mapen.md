# Contexto do projeto — MAPEN

**Projeto:** MAPEN — Monitoramento e Análise de Perdas Energéticas na Rede
**Disciplina:** BD2026.1 — Banco de Dados (Cesar School), **Grupo 3**
**Site da disciplina:** https://sites.google.com/cesar.school/bd2026-1-grupo-3/
**Blitz Research (Figma):** https://www.figma.com/board/RCtvw7HAa3O6WOmlyvHbtz/Blitz-Research
**Última atualização:** 2026-08-08

---

## Problema

As **perdas de energia elétrica** são um dos principais desafios das distribuidoras:
geram impacto financeiro, operacional e na qualidade do serviço. Identificar **onde** as
perdas ocorrem e sua dimensão é o ponto de partida para direcionar investimentos.

## Solução (o que o MAPEN faz)

O MAPEN auxilia distribuidoras acompanhando as perdas energéticas por meio de dados de
medição:

1. compara a **energia distribuída** com a **energia consumida**
2. calcula **perdas**
3. identifica **regiões com maior criticidade**
4. traduz resultados em **indicadores financeiros** (redflags por área)

## Como este repositório alimenta o MAPEN

O repo é a **camada de dados** da pesquisa: mapear/baixar/organizar dados abertos para
o MAPEN. Pilares:

| Pilar | Dados | Onde |
|---|---|---|
| Consumo/carga (geo+tempo) | ONS por subsistema (horária 2000→2026), EPE/CCEE | `data/consumo/ons/` + `docs/consumo_energia_brasil.md` |
| Distribuição (rede) | ONS subestações/linhas, Zenodo Omã/Nigéria, SIGEL/EPE | `data/power_grid_maps/` + `docs/power_grid_maps.md` |
| Geo administrativo | Malha de UFs do IBGE (27 UFs) | `data/br_ufs.json` |

**Uso final do consumo (geo+temporal):** detectar **inconsistências entre distribuição
e consumo** de energia elétrica por área, acionando **redflags** por região/estado — ex.:
área com alto consumo e baixa capacidade de rede, ou desvio perda/consumo acima do
esperado. (Ex.: `src/plot_br_consumo_rede.py` — calor de consumo + rede no mesmo mapa.)

**Abordagem de modelagem:** **ML clássica e/ou redes neurais** para identificar os
padrões de perda/inconsistência (ex.: detecção de anomalia nas séries, desvio
esperado-vs-observado distribuído vs consumido).

**Subprojeto (visão computacional):** leitura automática do display do medidor por
CV/OCR. **Saiu deste repo em 2026-08-10** → projeto `leiturista` em
`~/Developer/leiturista` (desafio Neoenergia, Projeto 4).

## Escopo

- **Foco:** energia elétrica.
- **Fora do foco** (baixados a pedido): gás (`grdf-*`), água (`ud-smart-city`).

## Docs relacionados

- `origem_dos_dados.md` — origem de cada dataset baixado
- `consumo_energia_brasil.md` — séries de consumo (geo+temporal)
- `power_grid_maps.md` — mapas de rede
- `perdas_energia_brasil.md`, `modelagem_redflags.md`, `redflags_perdas_prototipo.md`
