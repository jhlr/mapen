# MAPEN — Monitoramento e Análise de Perdas Energéticas na Rede

Camada de dados do projeto MAPEN: mapeia, baixa e organiza dados abertos do setor
elétrico brasileiro para comparar **energia distribuída vs energia consumida**,
calcular **perdas** e acionar **redflags por área** (UF/distribuidora) quando o desvio
foge do esperado.

**Disciplina:** BD2026.1 — Banco de Dados (Cesar School), Grupo 3
Site: https://sites.google.com/cesar.school/bd2026-1-grupo-3/
Blitz Research (Figma): https://www.figma.com/board/RCtvw7HAa3O6WOmlyvHbtz/Blitz-Research

## Problema

Perdas de energia elétrica geram impacto financeiro, operacional e na qualidade do
serviço das distribuidoras. Identificar **onde** as perdas ocorrem e sua dimensão é o
ponto de partida para direcionar investimentos.

## O que este repo faz

1. Baixa e organiza dados abertos de consumo/carga (ONS, EPE, CCEE/ANEEL SAMP) e de
   rede de distribuição (ONS subestações/linhas, Zenodo).
2. Cruza energia distribuída x consumida por UF/mês e calcula perda relativa.
3. Detecta **redflags**: perda relativa fora da faixa histórica (z-score sazonal > 2),
   por UF e por distribuidora.
4. Plota mapas de calor (consumo, rede, perdas) sobre a malha de UFs do Brasil.

## Estrutura

```
mapen/
├── data/                  # datasets baixados e derivados (não versionado, ver abaixo)
├── src/                   # scripts avulsos de dados/plot
│   ├── ons_load.py                # baixa datasets do portal ONS (CKAN)
│   ├── redflags_perdas.py         # cruza EPE + SAMP, calcula perdas e redflags
│   ├── plot_br_grid.py            # mapa da rede de distribuição
│   ├── plot_br_consumo.py         # mapa de calor de consumo por subsistema
│   └── plot_br_consumo_rede.py    # calor de consumo + rede no mesmo mapa
└── docs/                  # documentação do projeto (origem dos dados, modelagem, etc.)
```

## Dados

Os dados **não são versionados neste repo** (`data/` está no `.gitignore` — datasets
abertos são grandes e regeráveis a partir das fontes). Origem, licença e granularidade
de cada dataset estão documentadas em [`docs/origem_dos_dados.md`](docs/origem_dos_dados.md).

Fontes principais:

| Pilar | Dados | Fonte |
|---|---|---|
| Consumo/carga (geo+tempo) | Carga horária por subsistema (2000→2026) | ONS, EPE/CCEE |
| Perdas por distribuidora | Saldo/Perdas na Distribuição (2003→2026) | ANEEL SAMP-Balanço |
| Distribuição (rede) | Subestações/linhas | ONS, Zenodo |
| Geo administrativo | Malha de UFs | IBGE |

Escopo: **energia elétrica**. Datasets de gás (`grdf-*`) e água (`ud-smart-city`) foram
baixados a pedido mas estão fora do foco.

## Uso

```bash
# baixar dados do ONS
.venv/bin/python src/ons_load.py <dataset-id> [--ano YYYY]

# calcular perdas e redflags (gera CSVs em data/analise/)
.venv/bin/python src/redflags_perdas.py [--plot] [--uf PE]

# mapas
.venv/bin/python src/plot_br_grid.py
.venv/bin/python src/plot_br_consumo.py
.venv/bin/python src/plot_br_consumo_rede.py
```

Requer Python ≥ 3.11 e o ambiente virtual do projeto (`.venv/`).

## Docs

- [`docs/contexto_mapen.md`](docs/contexto_mapen.md) — visão geral do projeto
- [`docs/origem_dos_dados.md`](docs/origem_dos_dados.md) — origem de cada dataset
- [`docs/consumo_energia_brasil.md`](docs/consumo_energia_brasil.md) — séries de consumo
- [`docs/power_grid_maps.md`](docs/power_grid_maps.md) — mapas de rede
- [`docs/perdas_energia_brasil.md`](docs/perdas_energia_brasil.md) — perdas de energia
- [`docs/modelagem_redflags.md`](docs/modelagem_redflags.md) — abordagem de modelagem
- [`docs/redflags_perdas_prototipo.md`](docs/redflags_perdas_prototipo.md) — protótipo de redflags

## Fora deste repo

O subprojeto de visão computacional (leitura automática de displays de medidores via
CV/OCR) saiu deste repo em 2026-08-10 e virou o projeto `leiturista` (desafio
Neoenergia, Projeto 4).
