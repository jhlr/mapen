# AGENTS.md — MAPEN

Regras deste projeto (somam-se às regras globais de `~/.config/opencode/AGENTS.md`).

## Contexto

- **MAPEN** — Monitoramento e Análise de Perdas Energéticas na Rede.
- Disciplina **BD2026.1 (Cesar School)**, Grupo 3.
- Site: https://sites.google.com/cesar.school/bd2026-1-grupo-3/ | Figma (Blitz Research): https://www.figma.com/board/RCtvw7HAa3O6WOmlyvHbtz/Blitz-Research
- Contexto completo em `docs/contexto_mapen.md`.

## Objetivos da pesquisa

Montar a **camada de dados** do MAPEN: dados abertos que permitam comparar **energia
distribuída vs energia consumida** e **acionar redflags por área** (região/estado)
quando houver inconsistência/perda. Pilares:

1. **Consumo/carga (geo+temporal)** — ONS por subsistema (horária 2000→2026), EPE/CCEE por classe/UF.
2. **Distribuição** — mapas de rede (ONS subestações/linhas, Zenodo).
3. **Geo administrativo** — malha UF/município IBGE p/ ancorar tudo no mapa.

**Abordagem de modelagem:** usar **ML clássica e/ou redes neurais** para identificar os
padrões de perda/inconsistência mais facilmente (ex.: detecção de anomalia nas séries de
consumo, desvio esperado vs observado entre energia distribuída e consumida por área).

**Escopo: energia elétrica.** Gás (`grdf-*`) e água (`ud-smart-city`) estão baixados,
mas fora do foco — não investir neles.

> O **subprojeto de visão computacional (leitura de medidores)** saiu deste repo em
> 2026-08-10 e virou o projeto **`leiturista`** em `~/Developer/leiturista` (desafio
> Neoenergia, Projeto 4). O MAPEN hoje é **só camada de dados**.

## Estrutura do repo

```
mapen/
├── data/                  # datasets baixados, 1 pasta por dataset, arquivos flat
│   ├── grdf-*/            # fora do foco (gás)
│   ├── power_grid_maps/   # ons_brasil/ + zenodo/ (redes)
│   ├── consumo/           # ons/ samp/ samp_balanco/ epe/
│   └── br_ufs.json        # malha UF do IBGE (geoJSON)
├── src/                   # ferramentas de dados/plot avulsas (ons_load.py, plot_br_*.py)
├── docs/                  # toda documentação
└── .venv/                 # python (duckdb, matplotlib, huggingface_hub)
```

## Regras duras do projeto

1. **Documentar tudo em `docs/`** — qualquer descoberta, download, decisão, origem de
   dado vira doc commitável com data. Doc novo no chat SEM esperar pedido. Nada evaporar.
2. **Origem dos dados sempre documentada**: todo dataset baixado entra em
   `docs/origem_dos_dados.md` (fonte, autor, licença, granularidade, status) — antes de
   seguir. Datasets de consumo → `docs/consumo_energia_brasil.md`; mapas →
   `docs/power_grid_maps.md`.
3. **Ferramentas de dados/plot** ficam como `src/*.py` avulso; rodar com `.venv/bin/python`.
4. **Datasets em `data/`** — 1 pasta por dataset, arquivos flat (sem `.cache`/subpasta
   `data/`). Movido pra `data/` assim que concluído.
5. **Download sempre em background sem timeout** (`nohup ... > log 2>&1 &`) — nunca
   bloquear o turno. Log em `/tmp`. `HF_HUB_DISABLE_XET=1` p/ downloads grandes no HF
   (CDN xet trava). Nunca mover/renomear pasta com worker de download ativo.
6. **Escopo: energia elétrica.** Não expandir p/ gás/água sem pedido.
7. **Rodar com o `.venv` do projeto** (`mapen/.venv/bin/python`), não com o python do
   sistema.

## Rotinas

- **Consultar/download ONS:** `src/ons_load.py <dataset> [--ano YYYY]` → `data/consumo/ons/<dataset>/`.
- **Mapas:** `src/plot_br_grid.py` (rede), `src/plot_br_consumo.py` (calor por
  subsistema), `src/plot_br_consumo_rede.py` (calor + rede) → PNG no Desktop.
- **Status de downloads ativos:** checar `ps aux | grep -E 'retry_dl|hf download'` e logs `/tmp/*.log`.
- Ao final de tarefa longa, atualizar `docs/` com o que mudou (status/estrutura).

## FAQ de dados

- **Consumo em nível de bairro NÃO existe público** (LGPD/comercial). Máximo público:
  subsistema (ONS) → UF (CCEE) → município (PyPSA-Brasil, modelado). Bairro só via
  downscaling (Censo setores + ONS + clima).
- **ONS = carga do SIN** (medido), EPE/CCEE = consumo faturado. Diferença = perdas + MMGD.
- **O que baixar primeiro quando em dúvida**: ver `docs/consumo_energia_brasil.md` e
  `docs/origem_dos_dados.md` antes de duplicar trabalho.
