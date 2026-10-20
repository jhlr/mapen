# Relatório de alterações — ETL para o Neon

**Data:** 2026-10-20
**Escopo:** adaptação do ETL para ler dados tabulares locais do MAPEN e carregá-los
em tabelas PostgreSQL no Neon, usando exclusivamente `base_diaria.csv` e
`base_horaria.csv`, sem renomear os scripts existentes.

## Contexto

O fluxo anterior partia de um diretório genérico `dados_locais`, lia somente CSV,
deixava a transformação vazia e enviava os dados ao Neon por meio de uma conexão
configurada em `DATABASE_URL`. Isso não cobria os formatos documentados no MAPEN —
como Parquet do ONS/ANEEL e planilhas Excel da EPE — nem oferecia uma interface de
execução parametrizável para escolher a origem e a tabela de destino.

## O que foi alterado e por quê

### `src/extract.py` — extração de dados

- Mantido o nome do arquivo e a classe `Extract`.
- A leitura passou a aceitar CSV, Parquet (`.parquet` e `.pq`) e Excel `.xlsx`,
  tanto por arquivo quanto por diretório, inclusive subdiretórios.
- A lista de arquivos é ordenada para tornar a composição reproduzível.
- Cada linha recebe `source_file` e `source_row`, permitindo identificar o arquivo
  e a posição de origem após a consolidação.
- Colunas de entrada com esses nomes reservados geram erro explícito, para evitar
  sobrescrever metadados de rastreabilidade.
- Origem inexistente ou sem arquivos compatíveis interrompe o processo com erro,
  em vez de retornar um DataFrame vazio com aparência de sucesso.

**Motivo:** acomodar os formatos já usados nas fontes do MAPEN e conservar a
procedência dos registros carregados.

### `src/transform.py` — passagem dos dados pré-tratados

- Mantido o nome do arquivo e a classe `Transform`.
- A etapa retorna o DataFrame recebido sem modificar nomes de colunas, valores ou
  linhas.
- Não há preenchimento de ausentes, remoção de duplicatas, conversão de unidade
  ou outra limpeza; os dados de origem já chegam pré-tratados.

**Motivo:** respeitar o tratamento já realizado nos dados do projeto e evitar
alterações adicionais no esquema/conteúdo antes da carga.

### `src/load.py` — carga no Neon

- Mantido o nome do arquivo, a classe `Load` e o método `load_neon`.
- A conexão é obtida de `DATABASE_URL` ou pode ser injetada no construtor, o que
permite configurar credenciais sem colocá-las no código e testar a carga em banco
local.
- URLs `postgres://` e `postgresql://` são adaptadas ao driver Psycopg 3.
- Nomes de tabela são validados antes da gravação; estratégias aceitas são
`replace`, `append` e `fail`.
- A carga de DataFrame vazio é recusada; o engine é encerrado mesmo quando a
operação falha.

**Motivo:** manter o destino Neon solicitado, explicitar o comportamento quando a
tabela já existe e reduzir falhas de conexão/configuração ou nomes inválidos.

### `main.py` — integração das etapas

- O comando usa exclusivamente `av1-grupo-3-mapen/dados/base_diaria.csv` e
  `av1-grupo-3-mapen/dados/base_horaria.csv`; não aceita outros arquivos como
  entrada.
- Cada base é carregada na tabela de mesmo nome, sem extensão: `base_diaria` e
  `base_horaria`.
- Ambos os arquivos são verificados e extraídos antes da conexão/carga.
- O modo padrão é `replace`; os modos `append` e `fail` podem ser escolhidos na
linha de comando.
- As etapas informam o progresso, reportam o número de linhas carregadas e
propagam erros em vez de encerrar o fluxo como se tivesse sido bem-sucedido.

**Motivo:** limitar a carga às duas bases pré-tratadas solicitadas e impedir que
outros arquivos locais, em particular tarifas, entrem no pipeline.

### Dependências, documentação e testes

- `pyproject.toml`: incluídos `python-dotenv`, `sqlalchemy` e
`psycopg[binary]`, usados pela configuração e conexão PostgreSQL.
- `README.md`: adicionadas instruções de execução do ETL fixo para as bases
  diária e horária e referência à documentação do ETL.
- `docs/etl.md`: documenta as duas fontes permitidas e suas tabelas de destino,
  rastreabilidade, configuração, modos de carga e limites do fluxo.
- `tests/test_etl.py`: adicionados testes para leitura de CSV/Parquet/Excel,
preservação dos dados pré-tratados, carga local e validação do nome da tabela.
  Também cobre que o pipeline carrega apenas as duas bases e falha se alguma
  delas estiver ausente.

**Motivo:** tornar a integração utilizável e verificável sem depender de uma
conexão real com o banco para os testes.

## Validação realizada

- `pytest tests\test_etl.py -q`: **8 testes passaram**.
- Teste funcional local: extração, passagem dos dados sem alterações e carga SQL
foram executadas com sucesso, incluindo o modo `append`.
- `py_compile` dos scripts e testes e `main.py --help`: executados com sucesso.
- `git diff --check`: executado sem apontar erros de whitespace.
- **Nenhuma gravação foi feita no Neon** durante a validação. O carregamento real
depende da execução explícita do comando com `DATABASE_URL` configurada.

## Como executar

No Windows, a partir da raiz do repositório:

```powershell
.\.venv\Scripts\python.exe main.py
```

O comando carrega `base_diaria.csv` em `base_diaria` e `base_horaria.csv` em
`base_horaria`. Substitui as tabelas por padrão; para acrescentar registros,
use `--if-exists append`, ou `--if-exists fail` para falhar se uma tabela de
destino já existir. Antes de executar, confirme que `DATABASE_URL` aponta para o
banco e ambiente Neon desejados.

## Fora do escopo

- Os nomes `extract.py`, `transform.py` e `load.py` foram preservados.
- O pipeline usa somente `base_diaria.csv` e `base_horaria.csv`; dados de tarifas
  não são fonte nem destino deste ETL.
- A transformação permanece vazia por decisão de projeto: as entradas já estão
  pré-tratadas. A versão inicial deste ETL normalizava os nomes das colunas; essa
  mudança foi removida após a confirmação do requisito, e os testes/documentação
  foram atualizados para garantir o repasse sem alterações.
- O ETL não baixa datasets, não processa GeoJSON e não calcula perdas ou redflags;
  essas responsabilidades permanecem nos fluxos específicos do projeto.
- Alterações preexistentes em `.gitignore` e `src/plot_br_consumo_rede.py` não
fazem parte deste relatório.
