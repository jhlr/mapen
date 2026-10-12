"""Gera av1-grupo-3-mapen/racionalizacao.pdf a partir de racionalizacao.md (pandoc + navegador Chromium/Chrome).

Uso: python docs/ferramentas/gerar_relatorio_pdf.py
Precisa de pandoc e de um Chrome/Chromium; se o navegador não for achado, rode com CHROME=<caminho do executável>.
Confira depois o número de páginas: o corpo (até a seção 18) deve ficar em até 12 páginas, com o Anexo A depois.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PACOTE = RAIZ / "av1-grupo-3-mapen"
CSS = Path(__file__).resolve().parent / "relatorio.css"


def achar_navegador() -> str:
    candidatos = [os.environ.get("CHROME", "")]
    candidatos += [shutil.which(n) or "" for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")]
    candidatos += sorted(str(p) for p in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    candidatos += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                   "C:/Program Files/Google/Chrome/Application/chrome.exe",
                   "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    raise SystemExit("Não achei Chrome, Chromium ou Edge. Rode com CHROME=<caminho do executável>.")


def main() -> int:
    if not shutil.which("pandoc"):
        raise SystemExit("Não achei o pandoc (https://pandoc.org/installing.html).")
    navegador = achar_navegador()
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "relatorio.html"
        subprocess.run(["pandoc", "racionalizacao.md", "-f", "markdown", "-t", "html5", "-s", "--embed-resources",
                        "--resource-path=.", "--metadata", "pagetitle=AV1 Grupo 3 MAPEN", "-H", str(CSS), "-o", str(html)],
                       cwd=PACOTE, check=True)
        saida = PACOTE / "racionalizacao.pdf"
        subprocess.run([navegador, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={saida}", html.as_uri()], check=True, capture_output=True)
    print(f"Gerado: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
