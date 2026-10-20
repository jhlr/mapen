# ETL das bases diária e horária → Neon

**Atualizado em:** 2026-10-20

Pacote `src/mapen_etl/` (camadas `domain`/`application`/`infrastructure`/`interface`, contratos no
import-linter). Segue a estrutura **Extract → Transform → Load** exigida pelo professor:

| Etapa | Classe | Onde |
|---|---|---|
| Extract | `Extract.extract` | `infrastructure/extract.py` |
| Transform | `Transform.transform_data` | `application/transform.py` |
| Load | `Load.load_neon` | `infrastructure/load.py` |

Lê só `base_diaria.csv` e `base_horaria.csv` de `av1-grupo-3-mapen/dados/` e grava cada uma em uma
tabela de mesmo nome. Não lê outros arquivos (tarifas, por exemplo), não baixa dados e não calcula
perdas nem redflags.

| Arquivo | Tabela Neon |
|---|---|
| `base_diaria.csv` | `base_diaria` (`data` vira `TIMESTAMP`) |
| `base_horaria.csv` | `base_horaria` (`inicio_hora` vira `TIMESTAMP`) |

## Tratamento

Os CSVs já chegam pré-tratados, então o Transform repassa o conteúdo sem alterar (decisão do
projeto). O Extract tipa as colunas de data, deixa o pandas inferir os demais tipos (booleanos viram
`BOOLEAN`) e acrescenta `source_file` e `source_row` para rastrear a origem de cada linha. Colunas de
entrada com esses nomes são recusadas.

## Execução

Defina `DATABASE_URL` (URL PostgreSQL do Neon) no ambiente ou em `.env` na raiz; `.env` é ignorado
pelo git. Na raiz do repositório, com o ambiente virtual ativo e `pip install -e .` feito:

| | Ativar o ambiente | Rodar |
|---|---|---|
| macOS / Linux | `source .venv/bin/activate` | `mapen-etl` |
| Windows (PowerShell) | `.\.venv\Scripts\Activate.ps1` | `mapen-etl` |

Sem ativar o ambiente: `.venv/bin/mapen-etl` (macOS/Linux) ou `.\.venv\Scripts\mapen-etl.exe`
(Windows). Opções: `--if-exists replace|append|fail` e `--data-dir PASTA`.

- `replace` (padrão): apaga e recria a tabela a cada execução. É seguro porque as tabelas são
  derivadas dos CSVs versionados: reexecutar sempre produz o mesmo resultado.
- `append`: acrescenta; reexecutar duplica as linhas.
- `fail`: aborta se a tabela já existir.

As duas bases são lidas e validadas antes de qualquer gravação: arquivo ausente ou vazio aborta sem
tocar no Neon. Os testes (`tests/etl/`) usam SQLite; nenhuma gravação real no Neon foi feita.
