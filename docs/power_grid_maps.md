# Power grid maps — redes elétricas georreferenciadas (BR e internacionais)

- **Data:** 08/08/2026
- **Status:** ONS (BR) e Zenodo Omã/Nigéria **baixados**; GridKit/Stanford/SIGEL disponíveis, não baixados.

## O que é "power grid map"

Dados georreferenciados da infraestrutura elétrica: subestações (pontos), linhas de
transmissão/distribuição (traçados ou grafo topológico), postes, service points,
capacidade de transformação. **Não é** série temporal/consumo.

**Limite prático:** cobertura pública maciça existe para **transmissão** (rede
básica). A **fiação de distribuição de BT** (postes de rua/bairro) quase nunca é
pública de forma centralizada — no BR fica nas concessionárias (Copel, Enel, etc.),
fechada; o caminho aberto é OSM (camada `power`, incompleta).

## Brasil — baixado (ONS, CC BY 4.0)

Fonte: https://dados.ons.org.br (Sistema Interligado Nacional — rede de operação).

Arquivos em `mapen/data/power_grid_maps/ons_brasil/`:

| Arquivo | Conteúdo | Geometria |
|---|---|---|
| `SUBESTACAO.parquet` | 12 cols, subestações da rede de operação (subsistema, estado, agente, tensão, `id_estacao`, `num_barra`) | **sim** — `val_latitude`, `val_longitude` |
| `LINHA_TRANSMISSAO.parquet` | 37 cols: linhas de transmissão conectando subestações (`nom_subestacao_de`→`para`, `num_barra_de`/`para`), tensão kV, comprimento, resistência/reatância/shunt, capacidades operativas (longa/curta, verão/inverno) | **não direta** — montar grafo unindo as subestações; dá mapa topológico completo do SIN |
| `CAPACIDADE_TRANSFORMACAO.parquet` | 18 cols, transformadores da rede básica (MVA, tensões primário/secundário/terciário, `num_barra_*`) | não — referência barras |

URLs diretas (S3): `https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/{id}/...`
(`linha_transmissao/`, `subestacao/`, `capacidade-transformacao/`).

## Brasil — disponíveis, não baixados

1. **SIGEL — ANEEL** (`sigel.aneel.gov.br`) — shapefiles oficiais georreferenciados
   de todos os empreendimentos (geração, transmissão, subestações) e área de concessão
   das distribuidoras. Requer navegador/portal.
2. **EPE WebMap** (`gisepeprd2.epe.gov.br/WebMapEPE/`) — viewer do mapa de transmissão
   (Plano decenal/expansão).
3. **EPE — Mapa do Sistema Interligado Nacional** (PDF, publicado anualmente).
4. **Eletrobras — Mapas do Sistema Elétrico Brasileiro** (mapa, 2018).
5. **Zenodo `10.5281/zenodo.7478165`** (2022, CC BY 4.0) — dataset harmonizado do
   sistema elétrico BR para modelagem (PyPSA) — coordenadas de usinas/linhas.

## Internacional — baixado

**Zenodo `10.5281/zenodo.14873694`** (CC BY 4.0) → `mapen/data/power_grid_maps/zenodo/`
— dataset do paper *Geospatial Mapping of Large-Scale Electric Power Grids*
(Energy and AI, 2025), redes de distribuição/transmissão com coordenadas GIS:
- `Oman_Database_MZEC.zip` (9.7 MB) — rede de **distribuição** de Omã (MZEC):
  507k postes, 385k service points, 23.6k subestações
- `Nigeria_Database.zip` (0.3 MB) — rede de transmissão da Nigéria (~56k componentes)

## Internacional — disponíveis, não baixados

1. **GridKit** (`github.com/GridKit/GridKit`) — modelo oficioso da rede europeia
   ENTSO-E: buses, linhas, geradores, transformadores com **coordenadas geográficas**
   completas (releases de download; base do PyPSA-Eur).
2. **Stanford 2023** — *Geospatial mapping of distribution grid with ML and
   publicly-accessible multi-modal data* (Nature Comm 14:5006,
   `10.1038/s41467-023-39647-3`) — mapeamento de rede de **distribuição** (EUA)
   via imagens aéreas; dataset público acompanha.
3. **PyPSA-Earth / `earth-osm`** (`github.com/pypsa-meets-earth/earth-osm`) — API/CLI
   para extrair infra (linhas, subestações) do OSM para qualquer país, incluindo BR.
4. **Poles-on-Earth** (`github.com/TA-Geoforce/Poles-on-Earth`) — posições de postes
   do mundo todo via satélite (IA).
5. **Curadoria:** `github.com/ComplexNetTSP/ComplexNetWiki` → *PowerGrid-datasets.md*.

## Próximos passos sugeridos

1. **Gerar mapa topológico BR** a partir do ONS: nós = subestações (lat/long),
   arestas = linhas de transmissão (join por `num_barra`); plotar e exportar
   (GeoJSON/geopandas) → cobre todo o SIN.
2. Cruzar com o dataset BR de medidores (UFPR-AMR = Copel/PR) para contextualizar
   a região de estudo.
3. Se precisar de distribuição BT BR: extrair camada `power` do OSM no estado de
   interesse via `earth-osm` ou Overpass (incompleto, mas é o único aberto).
