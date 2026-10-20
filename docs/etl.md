# ETL das bases diária e horária → Neon

**Atualizado em:** 2026-10-20

O ETL em `main.py` usa exclusivamente os arquivos `base_diaria.csv` e
`base_horaria.csv` em `av1-grupo-3-mapen/dados/`. Não lê outros arquivos do
diretório nem dados de tarifas. Os scripts mantêm os nomes `src/extract.py`,
`src/transform.py` e `src/load.py`.

## Fontes e tabelas de destino

| Arquivo de entrada | Tabela Neon |
|---|---|
| `av1-grupo-3-mapen/dados/base_diaria.csv` | `base_diaria` |
| `av1-grupo-3-mapen/dados/base_horaria.csv` | `base_horaria` |

O ETL lê e valida os dois arquivos antes de iniciar a carga. Se qualquer um
estiver ausente ou sem linhas, encerra com erro e não inicia a conexão com o Neon.
Cada CSV é carregado separadamente em sua tabela correspondente.

## Tratamento dos dados

A extração lê os CSVs e adiciona `source_file` e `source_row` para registrar a
origem de cada linha. A transformação é intencionalmente neutra: preserva colunas,
valores e linhas já pré-tratados, sem limpeza ou conversões adicionais.

## Configuração e execução

Defina `DATABASE_URL` como a URL PostgreSQL do Neon no ambiente ou em `.env` na
raiz do repositório. Não versione credenciais. Instale as dependências do projeto
com `pip install -e .` no ambiente virtual e execute na raiz:

```powershell
.\.venv\Scripts\python.exe main.py
```

O modo padrão `--if-exists replace` substitui as duas tabelas a cada execução.
Use `--if-exists append` para acrescentar as linhas ou `--if-exists fail` para
interromper se qualquer tabela já existir. O modo `append` pode duplicar dados ao
reexecutar o pipeline.

O ETL não baixa arquivos, não processa outros datasets ou geometrias GeoJSON e
não calcula perdas ou redflags. Nenhuma tabela de tarifas é criada ou carregada
por este fluxo.
