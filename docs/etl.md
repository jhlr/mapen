# ETL das bases diária e horária → Neon

**Atualizado em:** 2026-10-20

## O que faz

Carrega as duas bases pré-tratadas da AV1 (CU-BEMS, andar 2, 8 ativos, 84 dias; descrição completa
dos campos em [`av1-grupo-3-mapen/dados/dicionario.md`](../av1-grupo-3-mapen/dados/dicionario.md))
em tabelas PostgreSQL no Neon:

| Arquivo (`av1-grupo-3-mapen/dados/`) | Tabela Neon | Linhas | Grão |
|---|---|---|---|
| `base_diaria.csv` | `base_diaria` | 672 | (`ativo`, `data`) |
| `base_horaria.csv` | `base_horaria` | 16.128 | (`ativo`, `inicio_hora`) |

Fora do escopo: outros arquivos da pasta (`recorte_minuto.csv.gz`, tarifas), download de dados,
GeoJSON, cálculo de perdas e redflags.

## Estrutura (Extract → Transform → Load)

Pacote `src/mapen_etl/`, nas mesmas camadas dos demais pacotes (dependências só para dentro,
verificadas pelo import-linter):

```
interface/cli.py              mapen-etl: argumentos e composição
application/carregar_bases.py caso de uso: Extract das duas bases, Transform, depois Load
application/transform.py      Transform.transform_data
application/portas.py         contratos de Extract e Load
infrastructure/extract.py     Extract.extract   (CSV → DataFrame)
infrastructure/load.py        Load.load_neon    (DataFrame → Neon)
domain/bases.py               as duas bases (arquivo, tabela, colunas de data) e os modos de carga
```

| Etapa | O que faz |
|---|---|
| Extract | Lê o CSV (UTF-8, com ou sem BOM), converte as colunas de data e acrescenta `source_file` e `source_row`. Recusa arquivo vazio e CSV que já traga essas duas colunas. |
| Transform | Repassa o conteúdo sem alterar: as bases já chegam pré-tratadas (decisão do projeto e requisito do professor). |
| Load | Valida o nome da tabela e o modo, grava com `DataFrame.to_sql` e encerra a conexão mesmo em erro. |

O caso de uso lê **as duas** bases antes de gravar qualquer tabela: arquivo ausente ou vazio aborta
sem tocar no Neon.

## Esquema das tabelas

Tipos inferidos pelo pandas e mapeados pelo SQLAlchemy para PostgreSQL.

| Coluna | `base_diaria` | `base_horaria` |
|---|---|---|
| `source_file` | `TEXT` | `TEXT` |
| `source_row` | `BIGINT` (linha do CSV, a partir de 1) | `BIGINT` |
| `data` / `inicio_hora` | `TIMESTAMP` | `TIMESTAMP` |
| `ativo` | `TEXT` | `TEXT` |
| `kwh`, `kw` | `DOUBLE PRECISION` | `DOUBLE PRECISION` |
| `minutos_validos` | `BIGINT` | n/a |
| `valido`, `feriado` | `BOOLEAN` | n/a |
| `expediente` | n/a | `BOOLEAN` |
| `tipo_dia` | `TEXT` | n/a |

Valores ausentes (dia com menos de 95% dos minutos) ficam `NULL`, não zero.

## Configuração

1. Crie um banco no Neon e copie a connection string (Dashboard → Connection Details).
2. Copie `.env.example` para `.env` na raiz e preencha `DATABASE_URL`. O `.env` é ignorado pelo
   git; a URL também pode vir de uma variável de ambiente. Prefixos `postgres://` e
   `postgresql://` são aceitos.
3. Instale o projeto no ambiente virtual (Python ≥ 3.11):

| | Criar e ativar o ambiente | Instalar |
|---|---|---|
| macOS / Linux | `python3 -m venv .venv && source .venv/bin/activate` | `pip install -e .` |
| Windows (PowerShell) | `py -m venv .venv; .\.venv\Scripts\Activate.ps1` | `pip install -e .` |

## Execução

Na raiz do repositório, com o ambiente ativo: `mapen-etl`. Sem ativar:
`.venv/bin/mapen-etl` (macOS/Linux) ou `.\.venv\Scripts\mapen-etl.exe` (Windows).

| Opção | Efeito |
|---|---|
| `--if-exists replace` (padrão) | apaga e recria cada tabela. Seguro porque elas são derivadas dos CSVs versionados: reexecutar dá sempre o mesmo resultado. |
| `--if-exists append` | acrescenta linhas; reexecutar **duplica**. |
| `--if-exists fail` | aborta se a tabela já existir. |
| `--data-dir PASTA` | pasta dos CSVs (padrão `av1-grupo-3-mapen/dados`, relativa ao diretório atual). |

Saída esperada:

```
Extract: av1-grupo-3-mapen/dados/base_diaria.csv
Extract: av1-grupo-3-mapen/dados/base_horaria.csv
Load: tabela 'base_diaria' (Neon)
Load: tabela 'base_horaria' (Neon)
base_diaria: 672 linhas gravadas.
base_horaria: 16128 linhas gravadas.
```

Conferência no Neon (SQL Editor ou `psql`):

```sql
SELECT count(*) FROM base_diaria;   -- 672
SELECT count(*) FROM base_horaria;  -- 16128
```

## Problemas comuns

| Mensagem | Causa e solução |
|---|---|
| `Configure DATABASE_URL ...` | variável ausente: crie o `.env` ou exporte a variável. |
| `Arquivo obrigatorio do ETL nao encontrado` | rode da raiz do repositório ou passe `--data-dir`. |
| `... contem colunas reservadas pelo ETL` | o CSV tem `source_file` ou `source_row`; renomeie na origem. |
| `Table '...' already exists` | modo `fail` e a tabela existe: use `replace` ou `append`. |
| erro de SSL / `sslmode` | a URL do Neon precisa terminar em `?sslmode=require`. |

## Testes

`pytest tests/etl`: 12 testes sobre SQLite, sem rede e sem credenciais. O ETL nunca foi executado
contra um Neon real nesta etapa; a primeira carga deve ser conferida com o SQL acima.
