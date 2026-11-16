"""Gera e verifica o conjunto fixo de instâncias do estudo."""

import hashlib
import json
import random

from experimentos.comum import RAIZ, codificar, substituir_arquivo

SEMENTE = 20261116
RAZAO_GEOMETRICA = 1.38
TAMANHOS = tuple(round(4 * RAZAO_GEOMETRICA ** k) for k in range(6))
PILOTO_MAX = 40
PASTA_DADOS = RAIZ / "dados"


def itens_aleatorios(n, semente):
    rng = random.Random(semente)
    return [(rng.randint(1, 50), rng.randint(1, 100)) for _ in range(n)]


def gravar_ou_conferir(caminho, conteudo):
    if caminho.exists():
        if caminho.read_bytes() != conteudo:
            raise ValueError(f"A entrada existente difere da geração esperada: {caminho}")
    else:
        temporario = caminho.with_suffix(caminho.suffix + ".tmp")
        temporario.write_bytes(conteudo)
        substituir_arquivo(temporario, caminho)


def gerar():
    PASTA_DADOS.mkdir(exist_ok=True)
    manifesto = []

    def registrar(identificador, serie, itens, w, semente):
        nome = f"{identificador}.txt"
        conteudo = codificar(itens, w)
        gravar_ou_conferir(PASTA_DADOS / nome, conteudo)
        manifesto.append({
            "id": identificador, "serie": serie, "n": len(itens), "W": w,
            "semente": semente, "arquivo": nome,
            "sha256": hashlib.sha256(conteudo).hexdigest(),
        })

    for n in TAMANHOS:
        semente = SEMENTE + n
        registrar(f"principal_n{n:02}", "principal", itens_aleatorios(n, semente), 20*n, semente)

    n = 12
    semente = SEMENTE + n
    itens = itens_aleatorios(n, semente)
    for w in (0, 240, 2400, 24000):
        registrar(f"capacidade_w{w:05}", "capacidade", itens, w, semente)
    registrar("peso_zero", "perfil", [(0, v) for _, v in itens], 240, semente)
    registrar("peso_excessivo", "perfil", [(241, v) for _, v in itens], 240, semente)

    for n in range(TAMANHOS[-1], PILOTO_MAX + 1):
        semente = SEMENTE + n
        registrar(f"piloto_n{n:02}", "piloto", itens_aleatorios(n, semente), 20*n, semente)

    dados = (json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    gravar_ou_conferir(PASTA_DADOS / "manifesto.json", dados)
    return manifesto


if __name__ == "__main__":
    print(f"{len(gerar())} instâncias verificadas em {PASTA_DADOS}.")
