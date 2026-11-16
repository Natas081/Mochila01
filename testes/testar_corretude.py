"""Testa os quatro executáveis por stdin e compara a um oráculo independente."""

import argparse
import itertools
import random
import subprocess
import unittest

from experimentos.comum import PROGRAMAS, RAIZ, codificar, comando, compilar, executar


def oraculo(itens, capacidade):
    return max(
        sum(valor for _, valor in subconjunto)
        for tamanho in range(len(itens) + 1)
        for subconjunto in itertools.combinations(itens, tamanho)
        if sum(peso for peso, _ in subconjunto) <= capacidade
    )


class Corretude(unittest.TestCase):
    def comparar(self, itens, capacidade, esperado):
        for linguagem, algoritmo in PROGRAMAS:
            with self.subTest(linguagem=linguagem, algoritmo=algoritmo,
                              itens=itens, capacidade=capacidade):
                saida = executar(linguagem, algoritmo, codificar(itens, capacidade),
                                 timeout=5)
                self.assertEqual(saida["otimo"], esperado)
                self.assertIs(type(saida["otimo"]), int)
                self.assertIs(type(saida["tempo_ns"]), int)
                self.assertGreaterEqual(saida["tempo_ns"], 0)

    def test_casos_conhecidos(self):
        casos = [
            ([], 0, 0), ([], 7, 0), ([(2, 9)], 0, 0),
            ([(5, 10), (6, 14)], 4, 0), ([(1, 5), (2, 5), (3, 5)], 3, 10),
            ([(0, 8), (0, 3), (2, 5)], 0, 11), ([(0, 0)], 0, 0),
            ([(0, 8), (0, 3), (2, 5)], 2, 16),
            ([(2, 3), (3, 4), (4, 5), (5, 6)], 5, 7),
            ([(10, 60), (20, 100), (30, 120)], 50, 220),
            ([(0, (1 << 63) - 1)], 0, (1 << 63) - 1),
            ([(1, (1 << 53) + 1), (1, 1)], 2, (1 << 53) + 2),
        ]
        for itens, capacidade, esperado in casos:
            self.comparar(itens, capacidade, esperado)

    def test_aleatorios_reproduziveis(self):
        rng = random.Random(1819)
        for n in range(13):
            for _ in range(2):
                itens = [(rng.randrange(16), rng.randrange(41)) for _ in range(n)]
                capacidade = rng.randrange(41)
                self.comparar(itens, capacidade, oraculo(itens, capacidade))

    def test_entradas_invalidas(self):
        casos = [
            b"", b"0", b"-1 5", b"1 -1 0 0", b"1 5 -2 9", b"1 5 2 -9",
            b"1 5 2", b"0 5 1", b"1 5 1 x", b"1 5 1 1.0", b"0 1\x1a extra",
            b"1 1 +0 0", b"0 9223372036854775808",
            b"2 1 1 9223372036854775807 1 1", b"2 1 9223372036854775807 1 1 1",
        ]
        for linguagem, algoritmo in PROGRAMAS:
            for entrada in casos:
                with self.subTest(programa=(linguagem, algoritmo), entrada=entrada):
                    processo = subprocess.run(comando(linguagem, algoritmo), input=entrada,
                                              capture_output=True, cwd=RAIZ, timeout=5)
                    self.assertEqual(processo.returncode, 2)
                    self.assertFalse(processo.stdout)
                    self.assertTrue(processo.stderr)

    def test_metricas_de_memoria(self):
        entrada = codificar([(0, 5), (2, 9)], 3)
        for linguagem, algoritmo in PROGRAMAS:
            with self.subTest(programa=(linguagem, algoritmo)):
                proc = executar(linguagem, algoritmo, entrada, "--mem-processo", timeout=5)
                self.assertEqual(proc["otimo"], 14)
                self.assertGreater(proc["base_ws_bytes"], 0)
                self.assertGreaterEqual(proc["pico_ws_bytes"], proc["pico_base_ws_bytes"])
                aux = executar(linguagem, algoritmo, entrada, "--mem-aux", timeout=5)
                self.assertEqual(aux["otimo"], 14)
                if linguagem == "C":
                    esperado = 3 * 4 * 8 if algoritmo == "programacao_dinamica" else 0
                    self.assertEqual(aux["aux_c_heap_bytes"], esperado)
                else:
                    self.assertGreater(aux["aux_py_bytes"], 0)


def validar():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Corretude)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    if not resultado.wasSuccessful():
        raise SystemExit("Corretude falhou. Experimentos interrompidos.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcc", default="gcc")
    parser.add_argument("--sem-compilar", action="store_true")
    args = parser.parse_args()
    if not args.sem_compilar:
        compilar(args.gcc)
    validar()
