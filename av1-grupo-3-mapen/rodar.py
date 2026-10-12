"""Roda o pacote da AV1 do começo ao fim e confere o resultado de cada passo.

Uso (na pasta av1-grupo-3-mapen, com qualquer Python 3.11 ou mais novo, sem instalar nada antes).
No Windows use `py rodar.py` se `python` não for reconhecido:

    python rodar.py                # cria .venv, instala as dependências, roda os 4 passos e abre o painel
    python rodar.py --sem-abrir    # idem, sem abrir o navegador

Só usa a biblioteca padrão. Sai com código 0 se todos os passos confirmaram o valor esperado
e com código 1 se algum falhou. Um passo marcado PULADO (Node ausente) não conta como falha.
O painel só abre se nenhum passo falhou. É um arquivo HTML local: não usa porta nem servidor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import venv
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
VERSIONADOS = [
    RAIZ / "dados" / "base_diaria.csv",
    RAIZ / "dados" / "base_horaria.csv",
    RAIZ / "dashboard" / "dados.js",
    RAIZ / "evidencias" / "resultados_python.json",
]
DESVIO_ESPERADO = "5.3248"  # z1_AC1, 2018-11-12, referência A (seção 7 do relatório)

resultados: list[tuple[str, str, str]] = []

# Windows: o console ou o redirecionamento podem usar uma codificação sem acentos (cp1252, cp850).
for _fluxo in (sys.stdout, sys.stderr):
    if (_fluxo.encoding or "").lower().replace("-", "") != "utf8":
        _fluxo.reconfigure(encoding="utf-8", errors="replace")


def python_do_venv() -> Path:
    return VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def rodar(cmd: list[str | Path]) -> tuple[int, str]:
    # PYTHONUTF8 faz os scripts filhos lerem e escreverem em UTF-8 também no Windows (padrão lá: cp1252).
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    p = subprocess.run([str(c) for c in cmd], cwd=RAIZ, env=env, capture_output=True)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", errors="replace")


def registrar(passo: str, status: str, detalhe: str) -> None:
    resultados.append((passo, status, detalhe))
    print(f"[{status:<6}] {passo}: {detalhe}", flush=True)


def hashes() -> dict[Path, str]:
    # Ignora a diferença de fim de linha (CRLF no Windows com autocrlf, LF no Linux e no Mac).
    return {a: hashlib.sha256(a.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for a in VERSIONADOS}


def preparar_ambiente() -> bool:
    if sys.version_info < (3, 11):
        registrar("0 · ambiente", "FALHOU", f"Python {sys.version.split()[0]}; precisa de 3.11 ou mais novo")
        return False
    py = python_do_venv()
    if not py.exists():
        print("Criando .venv ...", flush=True)
        venv.create(VENV, with_pip=True)
    cod, saida = rodar([py, "-m", "pip", "install", "-q", "-r", "requirements.txt"])
    if cod != 0:
        registrar("0 · ambiente", "FALHOU", "pip install falhou (sem internet?). Fim da saída:\n" + saida[-600:])
        return False
    registrar("0 · ambiente", "OK", f"Python {sys.version.split()[0]}, dependências de requirements.txt instaladas em .venv")
    return True


def passo1_pipeline() -> None:
    antes = hashes()
    cod, saida = rodar([python_do_venv(), "codigo/av1_desvio.py"])
    if cod != 0:
        registrar("1 · av1_desvio.py", "FALHOU", "saiu com erro:\n" + saida[-600:])
        return
    depois = hashes()
    mudou = [a.relative_to(RAIZ).as_posix() for a in VERSIONADOS if antes[a] != depois[a]]
    if mudou:
        registrar("1 · av1_desvio.py", "FALHOU", "regenerou arquivos diferentes dos versionados: " + ", ".join(mudou))
    else:
        registrar("1 · av1_desvio.py", "OK", "bases, dados.js e resultados regenerados, idênticos aos do pacote")


def passo2_conta_independente() -> None:
    cod, saida = rodar([python_do_venv(), "codigo/conta_independente.py", "z1_AC1", "2018-11-12", "A"])
    ok = cod == 0 and f"desvio={DESVIO_ESPERADO}" in saida and saida.strip().endswith("OK")
    registrar("2 · conta independente", "OK" if ok else "FALHOU",
              f"z1_AC1, 12/11, referência A: desvio +{DESVIO_ESPERADO} kWh" if ok else "saída diferente do esperado:\n" + saida[-400:])


def passo3_conferencia_cruzada() -> None:
    node = shutil.which("node")
    if not node:
        registrar("3 · conferência cruzada", "PULADO", "Node não encontrado (https://nodejs.org); instale para rodar este passo")
        return
    cod, saida = rodar([node, "codigo/conferencia_cruzada.js"])
    m = re.search(r"\{.*\}", saida)
    dados = json.loads(m.group(0)) if m else {}
    ok = cod == 0 and dados.get("falhas") == 0
    registrar("3 · conferência cruzada", "OK" if ok else "FALHOU",
              f"{dados.get('comparacoes')} comparações painel (JS) × Python, 0 falhas" if ok else "saída diferente do esperado:\n" + saida[-400:])


def passo4_testes() -> None:
    cod, saida = rodar([python_do_venv(), "-m", "pytest", "codigo", "-q"])
    resumo = (re.findall(r"\d+ passed[^\n]*", saida) or ["sem resumo do pytest"])[-1]
    registrar("4 · testes (pytest)", "OK" if cod == 0 else "FALHOU", resumo if cod == 0 else saida[-600:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sem-abrir", action="store_true", help="não abre dashboard/index.html no navegador no fim")
    args = ap.parse_args()

    print(f"Pacote: {RAIZ}\n")
    if preparar_ambiente():
        passo1_pipeline()
        passo2_conta_independente()
        passo3_conferencia_cruzada()
        passo4_testes()

    falhas = [r for r in resultados if r[1] == "FALHOU"]
    puladas = [r for r in resultados if r[1] == "PULADO"]
    print()
    if falhas:
        print(f"RESULTADO: FALHOU ({len(falhas)} passo(s)). Veja as mensagens acima.")
    else:
        print("RESULTADO: OK" + (f" ({len(puladas)} passo pulado, veja acima)" if puladas else ""))
        painel = RAIZ / "dashboard" / "index.html"
        print(f"Painel: {painel}")
        if not args.sem_abrir:
            if webbrowser.open(painel.as_uri()):
                print("Abrindo o painel no navegador ...")
            else:
                print("Não consegui abrir o navegador sozinho. Abra o arquivo acima com duplo clique,")
                print("ou rode 'python -m http.server' dentro de dashboard/ e acesse http://localhost:8000")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
