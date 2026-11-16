"""Coleta de memória em processos próprios, sem cronômetro de desempenho."""

from experimentos.comum import executar

REPETICOES = 3
CAMPOS = ("base_ws_bytes", "pico_base_ws_bytes", "pico_ws_bytes",
          "aux_py_bytes", "aux_c_heap_bytes")


def medir(linguagem, algoritmo, entrada, timeout):
    processo = executar(linguagem, algoritmo, entrada, "--mem-processo", timeout=timeout)
    auxiliar = executar(linguagem, algoritmo, entrada, "--mem-aux", timeout=timeout)
    if processo["otimo"] != auxiliar["otimo"]:
        raise RuntimeError("As duas execuções de memória retornaram ótimos diferentes.")

    atual, pico_base, pico = (processo[campo] for campo in CAMPOS[:3])
    if not 0 < atual <= pico_base <= pico:
        raise RuntimeError(f"Contadores de memória inconsistentes: {processo}")
    campo_aux = "aux_py_bytes" if linguagem == "Python" else "aux_c_heap_bytes"
    if type(auxiliar[campo_aux]) is not int or auxiliar[campo_aux] < 0:
        raise RuntimeError(f"Contador auxiliar inválido: {auxiliar}")
    return {**processo, **auxiliar}
