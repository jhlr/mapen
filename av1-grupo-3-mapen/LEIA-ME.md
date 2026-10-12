# AV1 · Grupo 3 · MAPEN/MAPPEN

Pergunta: em quais ativos e dias o consumo ficou acima ou abaixo de uma referência, e o que investigar primeiro? Dado **real público** (CU-BEMS, andar 2, 2018); referência **estimada**. Não é cliente do MAPEN, não prova desperdício nem economia.

## Abrir o painel
`dashboard/index.html` (duplo clique). Estado por URL: `?ativo=z1_AC1&de=2018-11-04&ate=2018-12-01&ref=A`.

## Ordem de reprodução (pasta `av1-grupo-3-mapen/`)
```
python codigo/av1_desvio.py                       # recalcula bases e dashboard/dados.js a partir de dados/recorte_minuto.csv.gz
python codigo/av1_desvio.py --fonte <2018Floor2.csv>   # opcional: refaz o recorte e o registro de qualidade
python codigo/conta_independente.py z1_AC1 2018-11-12 A
node codigo/conferencia_cruzada.js                # painel (JS) x Python
python -m pytest codigo -q
```
Requisitos: Python 3.14 com pandas 3 e numpy; Node (só para a conferência cruzada). Original do dado: https://doi.org/10.6084/m9.figshare.11726517 (CC BY 4.0, Pipattanasomporn et al. 2020).

## Mapa
| Pasta/arquivo | Conteúdo |
|---|---|
| `racionalizacao.pdf` / `.md` | relatório (modelo do professor, seções 1 a 18 + anexo) |
| `dados/` | recorte por minuto, bases diária e horária, `dicionario.md` |
| `codigo/` | pipeline, conta independente, conferência cruzada, testes |
| `dashboard/` | painel estático (HTML, CSS, JS, `dados.js`) |
| `evidencias/` | rascunho, versões do painel, captura anotada, casos (E4), qualidade, contrastes, resultados |

## Pendente do grupo
Teste de leitura com pessoa externa (seção 12) e contribuições individuais (seção 16): marcados **PENDENTE** no relatório.
