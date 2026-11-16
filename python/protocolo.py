"""Entrada e instrumentação comuns aos dois executáveis Python."""

import argparse
import json
import sys
from time import perf_counter_ns

MAX_INTEIRO = (1 << 63) - 1
MAX_TOKEN = 19


def ler_instancia(entrada, max_itens=MAX_INTEIRO):
    # Separadores ASCII e dígitos decimais, iguais aos aceitos pelo leitor C.
    tokens = (token for linha in entrada for token in linha.split())

    def inteiro():
        token = next(tokens, b"")
        if not 1 <= len(token) <= MAX_TOKEN or not token.isdigit():
            raise ValueError("esperado inteiro decimal não negativo de até 19 dígitos")
        valor = int(token)
        if valor > MAX_INTEIRO:
            raise ValueError("inteiro acima de 2^63 - 1")
        return valor

    n, capacidade = inteiro(), inteiro()
    if n > max_itens:
        raise ValueError(f"esta implementação aceita no máximo {max_itens} itens")
    itens = []
    pesos = valores = 0
    for _ in range(n):
        peso, valor = inteiro(), inteiro()
        pesos += peso
        valores += valor
        if pesos > MAX_INTEIRO or valores > MAX_INTEIRO:
            raise ValueError("a soma dos pesos e a soma dos valores devem caber em 63 bits")
        itens.append((peso, valor))
    if next(tokens, None) is not None:
        raise ValueError("dados extras depois do último item")
    return itens, capacidade


def memoria_processo(resolver, itens, capacidade):
    """Mede o working set com a mesma API usada pelas versões C."""
    import ctypes
    from ctypes import wintypes

    class Contadores(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("falhas", wintypes.DWORD),
            *[(nome, ctypes.c_size_t) for nome in (
                "pico", "atual", "pico_paginavel", "paginavel",
                "pico_nao_paginavel", "nao_paginavel", "paginacao", "pico_paginacao",
            )],
        ]

    processo_atual = ctypes.WinDLL("kernel32").GetCurrentProcess
    processo_atual.argtypes = []
    processo_atual.restype = wintypes.HANDLE
    consultar = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    consultar.argtypes = [wintypes.HANDLE, ctypes.POINTER(Contadores), wintypes.DWORD]
    consultar.restype = wintypes.BOOL
    processo = processo_atual()
    contadores = Contadores()
    contadores.cb = ctypes.sizeof(contadores)

    def medir():
        if not consultar(processo, ctypes.byref(contadores), contadores.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return contadores.atual, contadores.pico

    base, pico_base = medir()
    otimo = resolver(itens, capacidade)
    _, pico = medir()
    return {"otimo": otimo, "base_ws_bytes": base,
            "pico_base_ws_bytes": pico_base, "pico_ws_bytes": pico}


def executar(resolver, max_itens=MAX_INTEIRO):
    parser = argparse.ArgumentParser()
    modos = parser.add_mutually_exclusive_group()
    modos.add_argument("--mem-processo", action="store_true")
    modos.add_argument("--mem-aux", action="store_true")
    modos.add_argument("--valor", action="store_true")
    args = parser.parse_args()
    try:
        itens, capacidade = ler_instancia(sys.stdin.buffer, max_itens)
        if args.mem_processo:
            if sys.platform != "win32":
                raise ValueError("a medição do working set requer Windows")
            resultado = memoria_processo(resolver, itens, capacidade)
        elif args.mem_aux:
            import tracemalloc

            tracemalloc.start(1)
            try:
                otimo = resolver(itens, capacidade)
                _, pico = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            resultado = {"otimo": otimo, "aux_py_bytes": pico}
        elif args.valor:
            resultado = {"otimo": resolver(itens, capacidade)}
        else:
            inicio = perf_counter_ns()
            otimo = resolver(itens, capacidade)
            duracao = perf_counter_ns() - inicio
            resultado = {"otimo": otimo, "tempo_ns": duracao}
        print(json.dumps(resultado))
    except (ValueError, OverflowError, MemoryError, OSError) as erro:
        print(f"Falha ao executar: {erro or type(erro).__name__}", file=sys.stderr)
        return 2
    return 0
