# Datasets públicos de energia para protótipo (custo por tarifa horária e ranking de equipamentos)

Data de acesso de todas as fontes: 2026-10-01. Dados baixados em `data/publicos/` (ignorado pelo git via `.gitignore`, linha `data/`).

## Limitação principal

Nenhum dataset abaixo é brasileiro. Eles demonstram o método (agregação por horário, ranking, custo por tarifa), não o comportamento de carga no Brasil (clima, equipamentos, hábitos, tarifa branca/ponta). Valores de kWh e curvas não devem ser apresentados como "consumo brasileiro".

## Comparação

| | CU-BEMS | BDG2 | COMBED | REFIT (não baixado) |
|---|---|---|---|---|
| Local / tipo | Bangkok, prédio de escritórios de 7 andares | 19 sites América do Norte e Europa, 1.636 prédios não residenciais | Bloco acadêmico e bloco de aulas, IIIT Delhi, Índia | 20 casas, Reino Unido |
| Nível de medição | Por zona: cada AC, iluminação e tomadas (kW) | Medidor geral do prédio (eletricidade, 1.578 medidores) | Por circuito: AHU, elevadores, luz, tomadas, UPS, total | Geral + por aparelho (W) |
| Período | 2018-07-01 a 2019-12-31 | 2016-01-01 a 2017-12-31 | ~1 mês (2014-06-02 a 2014-07-01) | 2013-10 a 2015-06 |
| Resolução | 1 min | 1 h | 30 s | 8 s |
| Tamanho | 748 MB (14 CSV) | 568 MB (zip) | 42 MB (zip, 207 MB descompactado) | 368 MB (.7z) |
| Licença | CC BY 4.0 | CC BY 4.0 (Zenodo) vs CC BY-SA (arquivo LICENSE do GitHub) | não declarada | CC BY 4.0 |
| Uso comercial | sim (com atribuição) | sim; conservador: tratar como BY-SA | incerto | sim (com atribuição) |
| Login | não | não | não | não |
| Baixado | sim | sim | sim | não |

## CU-BEMS

- Descrição: prédio de escritórios de 11.700 m2, 33 zonas, 7 andares. Fonte: https://www.nature.com/articles/s41597-020-00582-3 e https://pmc.ncbi.nlm.nih.gov/articles/PMC7371880/ (acessado 2026-10-01).
- Download sem login: https://doi.org/10.6084/m9.figshare.11726517 (arquivos via `https://ndownloader.figshare.com/files/<id>`, ids na API https://api.figshare.com/v2/articles/11726517).
- Licença: API do figshare retorna "CC BY 4.0" (https://creativecommons.org/licenses/by/4.0/). O artigo diz: "licensed under a Creative Commons Attribution 4.0 International License". CC BY 4.0 permite uso comercial com atribuição.
- Arquivos: `2018Floor1..7.csv` e `2019Floor1..7.csv` (+ 2 PDFs de manual de medidor, 8,6 MB, não baixados). Tamanhos conferidos byte a byte com a API.
- Colunas: `Date` e, por zona, `zN_ACk(kW)`, `zN_Light(kW)`, `zN_Plug(kW)`, `zN_S1(degC)`, `zN_S1(RH%)`, `zN_S1(lux)`. Andar 1 não tem sensores ambientais (12 colunas); andares 2-7 têm 30 a 37.
- Verificação local: 14 arquivos, 5.432.489 linhas no total; `2018Floor1.csv` tem 264.960 linhas x 12 colunas, de 2018-07-01 00:00 a 2018-12-31 23:59.
- Cuidados (artigo, PMC7371880): andares 3 e 4 com 10 a 20% de dados faltantes; sensores desligados de 2018-09-15 a 2019-03-05. Zona 3 de cada andar é escada sem ar-condicionado. Os valores em kW são por zona inteira (somas grandes, ex.: 45 kW em um AC na linha de exemplo).
- Limitação para equipamentos: a granularidade é "AC / iluminação / tomadas" por zona, não aparelhos individuais de tomada.

## BDG2 (Building Data Genome Project 2)

- Descrição: 3.053 medidores, 1.636 prédios, 2016-2017, horário (17.544 pontos por medidor). Fonte: https://github.com/buds-lab/building-data-genome-project-2 (README) e artigo https://doi.org/10.1038/s41597-020-00712-x (acessado 2026-10-01).
- Download sem login: Zenodo https://doi.org/10.5281/zenodo.3887306, arquivo `building-data-genome-project-2-v1.0.zip` (https://zenodo.org/api/records/3887306/files/buds-lab/building-data-genome-project-2-v1.0.zip/content). Também no Kaggle (citado no README; não verificado se exige login). Arquivos dentro do repositório GitHub são ponteiros Git LFS de ~133 bytes, por isso usar o zip.
- Licença: Zenodo declara "cc-by-4.0" (API https://zenodo.org/api/records/3887306). O arquivo LICENSE do GitHub começa com "Attribution-ShareAlike 4.0 Unported" (https://raw.githubusercontent.com/buds-lab/building-data-genome-project-2/master/LICENSE). Há conflito entre as duas fontes; ambas permitem uso comercial, BY-SA exige compartilhar derivados sob a mesma licença. Usar BY-SA como hipótese segura.
- Conteúdo do zip: `data/meters/{raw,cleaned}/<tipo>.csv`, `data/metadata/metadata.csv`, `data/weather/weather.csv` (+ notebooks).
- Colunas: `electricity_cleaned.csv` tem `timestamp` + uma coluna por medidor (`<site>_<uso>_<nome>`, ex.: `Panther_parking_Lorriane`). `metadata.csv` (32 colunas): `building_id, site_id, primaryspaceusage, sub_primaryspaceusage, sqm, lat, lng, timezone, electricity, ..., yearbuilt, numberoffloors, occupants, eui, ...`.
- Verificação local: `electricity_cleaned.csv` 17.544 linhas x 1.579 colunas (1.578 medidores), 2016-01-01 00:00 a 2017-12-31 23:00; `metadata.csv` 1.636 x 32. Zip testado (`testzip` sem erro). Usos principais: Education 617, Office 307, Entertainment/public assembly 204, Lodging/residential 168, Public services 166.
- Limitação: um medidor por prédio, sem separação por equipamento. Não é submedição.

## COMBED (IIIT Delhi)

- Descrição: dados de ~200 medidores Schneider em prédio acadêmico, coleta a cada 30 s, ~1 mês. Fonte: https://combed.github.io/ (acessado 2026-10-01).
- Download sem login: http://combed.github.io/downloads/combed.zip (44.205.382 bytes) e http://combed.github.io/downloads/combed.h5 (21.736.453 bytes, formato nilmtk; não baixado).
- Licença: não encontrado na página nem no repositório https://github.com/combed/combed.github.io (API de licença retorna 404). Uso comercial: incerto. Perguntar aos autores antes de qualquer uso além de estudo.
- Estrutura: 75 CSV em `iiitd/<Bloco>/<Grupo>/<id>/{Power,Energy,Current}.csv`. Grupos do Academic Block: AHU, Building Total Mains, Floor Total, Lifts, Light, Power, Power Sockets, UPS Sockets; Lecture Block: AHU, AHU-1..3, Building Total Mains, Floor Total.
- Colunas: arquivos sem cabeçalho, duas colunas: timestamp Unix em milissegundos e valor (Power em W). Verificado em `Academic Block/Building Total Mains/0/Power.csv`: 82.888 linhas (contando a primeira, lida como cabeçalho na checagem), de 2014-06-02 07:56 UTC a 2014-07-01 03:59 UTC.
- Mantido compactado em `data/publicos/combed/combed.zip` (descompactado seriam 207 MB; ler direto do zip).
- Limitação: um mês apenas; clima e uso indianos.

## REFIT (documentado, não baixado)

- 20 casas do Reino Unido, 8 s, 2013-10 a 2015-06, geral e por aparelho (9 canais por casa, segundo o artigo https://www.nature.com/articles/sdata2016122; não verificado nesta consulta). Fonte: https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements/ (acessado 2026-10-01).
- Download sem login, mesma página: "REFIT Power Data" 368 MB (.7z), versão bruta 666 MB. DOI 10.15129/31da3ece-f902-4e95-a093-e0a9536983c4. Licença da página: CC BY 4.0 (uso comercial: sim, com atribuição).
- Não baixado: somaria ~1,7 GB e estouraria o limite de 1,5 GB. Residencial, não comercial.
- Alternativa encontrada, também não baixada: CLEMD, Malásia, 8 circuitos de um prédio de faculdade, 1 s (arquivos de 101 a 164 MB), CC BY 4.0: https://pmc.ncbi.nlm.nih.gov/articles/PMC11156870/ (DOI do repositório https://doi.org/10.6084/m9.figshare.c.6946581; link de arquivo individual não verificado).

## Dataset brasileiro de submedição

Não encontrado. Buscas em 2026-10-01 (inglês e português; Zenodo, figshare, Mendeley, Scientific Data, Data in Brief) não retornaram nenhum dataset aberto brasileiro com medição por aparelho ou circuito. Encontrados apenas: dados agregados nacionais (https://basedosdados.org/dataset/3e31e540-81ba-4665-9e72-3f81c176adad; https://zenodo.org/records/7478165), um estudo de usos finais residenciais com 5.625 residências, 2005 (https://labeee.ufsc.br/pt-br/node/480; não verificado se os microdados são abertos) e um artigo NILM da Unesp (https://link.springer.com/article/10.1186/s42162-020-00131-7; não verificado se há dados públicos). Para dados brasileiros reais, o caminho é medir (a própria tomada IoT do projeto).

## Recomendação

1. Ranking de equipamentos: CU-BEMS (AC, iluminação e tomadas por zona, 1 min) como principal; COMBED (circuitos de AHU, elevador, luz, tomadas, UPS, 30 s) como segunda fonte, se a licença for esclarecida. REFIT serve se o foco for eletrodoméstico residencial (baixar fora do limite de espaço atual).
2. Custo de prédio inteiro por tarifa horária: BDG2 (hora a hora, 1.578 medidores, 2 anos, metadado de uso e área) para testar o cálculo em muitos perfis e comparar por tipo de uso; CU-BEMS para o caso de um prédio com resolução de minuto (soma das colunas `kW` por andar dá o total, dados faltantes nos andares 3 e 4).
3. Inadequado: BDG2 para ranking de equipamentos (só medidor geral); COMBED para análise sazonal ou anual (1 mês); qualquer um como estimativa de custo no Brasil (tarifa, clima e hábitos diferentes); CU-BEMS para identificar aparelhos individuais de tomada (agregado por zona).
4. Atribuição obrigatória (CC BY): citar Pipattanasomporn et al. 2020 (CU-BEMS) e Miller et al. 2020 (BDG2).

## Verificação do download

- `data/publicos/cu_bems/`: 14 CSV, 748 MB em disco, tamanhos conferidos com a API do figshare, 5.432.489 linhas.
- `data/publicos/bdg2/building-data-genome-project-2-v1.0.zip`: 595.266.464 bytes (568 MiB), igual ao Zenodo, `testzip` ok.
- `data/publicos/combed/combed.zip`: 42 MB, lido sem extrair.
- Total em disco: ~1,31 GiB (1,41 GB), abaixo de 1,5 GB.
