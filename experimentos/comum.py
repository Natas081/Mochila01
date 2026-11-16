"""Compilação e protocolo dos executáveis."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import sleep

RAIZ = Path(__file__).resolve().parents[1]
ALGORITMOS = ("forca_bruta", "programacao_dinamica")
PROGRAMAS = tuple((ling, alg) for alg in ALGORITMOS for ling in ("Python", "C"))
FLAGS = ("-std=c11", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror")


def compilar(gcc="gcc"):
    (RAIZ / "build").mkdir(exist_ok=True)
    for nome in ALGORITMOS:
        subprocess.run(
            [gcc, *FLAGS, f"c/{nome}.c", "c/protocolo.c",
             "-o", f"build/{nome}.exe", "-lpsapi"],
            cwd=RAIZ, check=True,
        )


def comando(linguagem, algoritmo):
    if linguagem == "Python":
        return [sys.executable, str(RAIZ / "python" / f"{algoritmo}.py")]
    return [str(RAIZ / "build" / f"{algoritmo}.exe")]


def executar(linguagem, algoritmo, entrada, modo=None, timeout=60):
    argumentos = [modo] if modo else []
    processo = subprocess.run(
        [*comando(linguagem, algoritmo), *argumentos], input=entrada,
        capture_output=True, cwd=RAIZ, timeout=timeout, check=False,
    )
    if processo.returncode != 0:
        erro = processo.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"{linguagem}/{algoritmo} (código {processo.returncode}): {erro}")
    return json.loads(processo.stdout)


def codificar(itens, capacidade):
    linhas = [f"{len(itens)} {capacidade}", *(f"{p} {v}" for p, v in itens)]
    return ("\n".join(linhas) + "\n").encode("ascii")


def substituir_arquivo(temporario, destino):
    """Repete a troca atômica se um processo do Windows segurar o arquivo."""
    for espera in (0.05, 0.1, 0.2, 0.4, 0.8, 1, 0):
        try:
            temporario.replace(destino)
        except PermissionError as erro:
            if not espera or getattr(erro, "winerror", None) not in (5, 32, 33):
                raise
            sleep(espera)
        else:
            return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compila os dois programas em C.")
    parser.add_argument("--gcc", default="gcc")
    compilar(parser.parse_args().gcc)
