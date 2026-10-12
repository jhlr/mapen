# Ferramentas para regerar os PDFs

Os dois PDFs da AV1 são gerados por script. Rodar na raiz do repositório.

| PDF | Comando | Precisa de |
|---|---|---|
| `av1-grupo-3-mapen/racionalizacao.pdf` (a partir de `racionalizacao.md`) | `python docs/ferramentas/gerar_relatorio_pdf.py` | pandoc e Chrome, Chromium ou Edge (`CHROME=<caminho>` se não achar) |
| `docs/av1-guia-do-painel-2026-10-12.pdf` | `python docs/ferramentas/gerar_guia_pdf.py` | `pip install -r docs/ferramentas/requirements-pdf.txt` e a fonte DejaVu Sans (`FONTES_DIR=<pasta>` se não achar) |

- Depois de regerar o relatório, confira o número de páginas: o corpo (até a seção 18) deve ficar em até 12 páginas, com o Anexo A depois. Depende da fonte do navegador: no Mac são 12 no total (corpo até a 9); o Linux gerava a versão anterior, mais longa, com 16.
- O guia tem os textos escritos dentro de `gerar_guia_pdf.py`; ao mudar o relatório, revise os trechos que citam números ou seções.
- `relatorio.css` é o estilo do PDF do relatório.
- Testado no Linux. Em Windows e Mac os caminhos do navegador e da fonte estão previstos, mas não foram testados.
