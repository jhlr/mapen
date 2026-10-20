# ETL das bases diária e horária → Neon

**Atualizado em:** 2026-10-20

Pacote `src/mapen_etl/` (camadas `domain`/`application`/`infrastructure`/`interface`, contratos no
import-linter). Lê só `base_diaria.csv` e `base_horaria.csv` de `av1-grupo-3-mapen/dados/` e grava
cada uma em uma tabela de mesmo nome. Não lê outros arquivos (tarifas, por exemplo), não baixa dados
e não calcula perdas nem redflags.

| Arquivo | Tabela Neon |
|---|---|
| `base_diaria.csv` | `base_diaria` (`data` vira `TIMESTAMP`) |
| `base_horaria.csv` | `base_horaria` (`inicio_hora` vira `TIMESTAMP`) |

## Tratamento

Os CSVs já chegam pré-tratados: não há etapa de transformação. A leitura só tipa as colunas de data,
deixa o pandas inferir os demais tipos (booleanos viram `BOOLEAN`) e acrescenta `source_file` e
`source_row` para rastrear a origem de cada linha. Colunas de entrada com esses nomes são recusadas.

## Execução

Defina `DATABASE_URL` (URL PostgreSQL do Neon) no ambiente ou em `.env` na raiz; `.env` é ignorado
pelo git. Depois de `pip install -e .`:

```bash
mapen-etl [--if-exists fail|append|replace] [--data-dir PASTA]
```

- `fail` (padrão): aborta se a tabela já existir; nada é apagado.
- `append`: acrescenta; reexecutar duplica as linhas.
- `replace`: apaga e recria a tabela. Só com pedido explícito.

As duas bases são lidas e validadas antes de qualquer gravação: arquivo ausente ou vazio aborta sem
tocar no Neon. Os testes (`tests/etl/`) usam SQLite; nenhuma gravação real no Neon foi feita.
