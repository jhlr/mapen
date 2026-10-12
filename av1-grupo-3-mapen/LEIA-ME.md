# AV1 · Grupo 3 · MAPEN/MAPPEN

Pergunta: em quais ativos e dias o consumo ficou acima ou abaixo de uma referência, e o que investigar primeiro? Dado **real público** (CU-BEMS, andar 2, 2018); referência **estimada**. Não é cliente do MAPEN, não prova desperdício nem economia.

## 1. Só ver o painel (não precisa instalar nada)

Abra `dashboard/index.html` com duplo clique no navegador. Funciona offline.

Se o navegador bloquear o arquivo local, rode `python -m http.server` dentro de `dashboard/` e abra `http://localhost:8000`.

Estado do painel pela URL: `index.html?ativo=z1_AC1&de=2018-11-04&ate=2018-12-01&ref=A`
(`ref` = A, B ou C; `de` e `ate` em AAAA-MM-DD, dentro de 2018-11-04 a 2018-12-01.)

## 2. Recalcular e conferir os números

**Jeito rápido:** com Python 3.11 ou mais novo, na pasta `av1-grupo-3-mapen`:

```
python rodar.py            # cria .venv, instala as dependências, roda os 4 passos e confere cada resultado
python rodar.py --abrir    # idem, e abre o painel no navegador no fim
```

Só usa a biblioteca padrão. Cada passo termina com `OK`, `FALHOU` ou `PULADO` (Node ausente) e o script sai com código 1 se algo falhar. Leva cerca de 20 segundos (a primeira vez inclui baixar pandas e numpy). Os passos manuais abaixo fazem a mesma coisa, um por um.


Requisitos: **Python 3.11 ou mais novo** (testado em 3.11, 3.12 e 3.13) e **Node** (só para o passo 3; testado com Node 22). Sem Node, `rodar.py` pula o passo 3.

```
cd av1-grupo-3-mapen
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # pandas, numpy, pytest
```

Depois, na ordem:

| Passo | Comando | Saída esperada |
|---|---|---|
| 1 | `python codigo/av1_desvio.py` | Imprime a sensibilidade e os rankings das referências A, B e C. Regrava `dados/base_*.csv`, `dashboard/dados.js` e `evidencias/resultados_python.json` com o mesmo conteúdo (se `git status` mostrar mudança, algo diverge) |
| 2 | `python codigo/conta_independente.py z1_AC1 2018-11-12 A` | `observado=289.4012 esperado=284.0763 desvio=5.3248 kWh` e `maior diferença absoluta = 0.00003 kWh -> OK` |
| 3 | `node codigo/conferencia_cruzada.js` | `{"comparacoes":2016,"maior_diferenca_abs":0.0001...,"falhas":0}` (o que importa é `"falhas":0`) |
| 4 | `python -m pytest codigo -q` | `5 passed` |

A conta do passo 2 usa só a biblioteca padrão do Python e lê o CSV bruto, sem reaproveitar código do pipeline.

### Refazer o recorte a partir do arquivo original (opcional)

O `dados/recorte_minuto.csv.gz` já está no pacote e basta para os passos acima. Para refazê-lo e o registro de qualidade, baixe `2018Floor2.csv` (cerca de 41 MB) do CU-BEMS (https://doi.org/10.6084/m9.figshare.11726517, CC BY 4.0, Pipattanasomporn et al. 2020) e rode:

```
python codigo/av1_desvio.py --fonte caminho/para/2018Floor2.csv
```

Isso **sobrescreve** `dados/recorte_minuto.csv.gz` e `evidencias/verificacoes_qualidade.json`. O arquivo original não vem no pacote.

## Mapa
| Pasta/arquivo | Conteúdo |
|---|---|
| `racionalizacao.pdf` / `.md` | relatório (modelo do professor, seções 1 a 18 + anexo) |
| `dados/` | recorte por minuto, bases diária e horária, `dicionario.md` |
| `codigo/` | pipeline, conta independente, conferência cruzada, testes |
| `dashboard/` | painel estático (HTML, CSS, JS, `dados.js`) |
| `evidencias/` | rascunho, versões do painel, captura anotada, casos (E4), qualidade, contrastes, resultados |
| `rodar.py` | roda e confere tudo (cria `.venv`, instala, passos 1 a 4) |
| `requirements.txt` | dependências Python dos passos 1, 2 e 4 |

## Pendente do grupo
Teste de leitura com pessoa externa (seção 12) e contribuições individuais (seção 16): marcados **PENDENTE** no relatório.
