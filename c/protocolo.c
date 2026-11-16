#include "protocolo.h"

#include <ctype.h>
#include <fcntl.h>
#include <inttypes.h>
#include <io.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define WIN32_LEAN_AND_MEAN
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include <windows.h>
#include <psapi.h>

static int ler_inteiro(uint64_t *resultado)
{
    int c;
    do {
        c = getchar();
    } while (isspace(c));

    uint64_t valor = 0;
    unsigned digitos = 0;
    while (c != EOF && !isspace(c)) {
        if (c < '0' || c > '9' || ++digitos > 19) {
            return 0;
        }
        unsigned digito = (unsigned)(c - '0');
        if (valor > (INT64_MAX - digito) / UINT64_C(10)) {
            return 0;
        }
        valor = valor * 10 + digito;
        c = getchar();
    }
    *resultado = valor;
    return digitos > 0;
}

static const char *ler_itens(Item *itens, size_t n)
{
    uint64_t pesos = 0, valores = 0;
    for (size_t i = 0; i < n; ++i) {
        if (!ler_inteiro(&itens[i].peso) || !ler_inteiro(&itens[i].valor)) {
            return "esperado um par (peso, valor) de inteiros nao negativos";
        }
        if (itens[i].peso > INT64_MAX - pesos || itens[i].valor > INT64_MAX - valores) {
            return "a soma dos pesos e a soma dos valores devem caber em 63 bits";
        }
        pesos += itens[i].peso;
        valores += itens[i].valor;
    }
    int c;
    do {
        c = getchar();
    } while (isspace(c));
    return c == EOF && !ferror(stdin) ? NULL : "dados extras ou erro na entrada";
}

static int falha(const char *erro)
{
    fprintf(stderr, "Falha ao executar: %s\n", erro);
    return 2;
}

int executar(int argc, char **argv, Solucionador resolver, uint64_t max_itens)
{
    enum { TEMPO, PROCESSO, AUXILIAR, VALOR } modo = TEMPO;
    if (argc == 2 && strcmp(argv[1], "--mem-processo") == 0) {
        modo = PROCESSO;
    } else if (argc == 2 && strcmp(argv[1], "--mem-aux") == 0) {
        modo = AUXILIAR;
    } else if (argc == 2 && strcmp(argv[1], "--valor") == 0) {
        modo = VALOR;
    } else if (argc != 1) {
        return falha("opcoes: --mem-processo, --mem-aux ou --valor");
    }

    /* O descritor 0 corresponde à entrada padrão no CRT do Windows. */
    if (_setmode(0, _O_BINARY) == -1) {
        return falha("nao foi possivel configurar a entrada");
    }
    uint64_t n, capacidade;
    if (!ler_inteiro(&n) || !ler_inteiro(&capacidade) || n > max_itens ||
        n > SIZE_MAX / sizeof(Item)) {
        return falha("cabecalho n W invalido ou acima do limite da implementacao");
    }
    Item *itens = n == 0 ? NULL : malloc((size_t)n * sizeof *itens);
    if (n != 0 && itens == NULL) {
        return falha("memoria insuficiente para a entrada");
    }
    const char *erro = ler_itens(itens, (size_t)n);
    if (erro != NULL) {
        free(itens);
        return falha(erro);
    }

    LARGE_INTEGER frequencia, inicio, fim;
    PROCESS_MEMORY_COUNTERS antes = {0}, depois = {0};
    antes.cb = sizeof antes;
    depois.cb = sizeof depois;
    if (modo == PROCESSO &&
        !GetProcessMemoryInfo(GetCurrentProcess(), &antes, sizeof antes)) {
        free(itens);
        return falha("GetProcessMemoryInfo falhou");
    }
    if (modo == TEMPO &&
        (!QueryPerformanceFrequency(&frequencia) || !QueryPerformanceCounter(&inicio))) {
        free(itens);
        return falha("QueryPerformanceCounter indisponivel");
    }
    uint64_t otimo;
    size_t aux_heap;
    erro = resolver(itens, (size_t)n, capacidade, &otimo, &aux_heap);
    if (modo == TEMPO && !QueryPerformanceCounter(&fim)) {
        erro = "QueryPerformanceCounter falhou";
    }
    if (modo == PROCESSO &&
        !GetProcessMemoryInfo(GetCurrentProcess(), &depois, sizeof depois)) {
        erro = "GetProcessMemoryInfo falhou";
    }
    free(itens);
    if (erro != NULL) {
        return falha(erro);
    }

    printf("{\"otimo\":%" PRIu64, otimo);
    if (modo == TEMPO) {
        uint64_t nanos = (uint64_t)((fim.QuadPart - inicio.QuadPart) * 1e9 /
                                    frequencia.QuadPart);
        printf(",\"tempo_ns\":%" PRIu64, nanos);
    } else if (modo == PROCESSO) {
        printf(",\"base_ws_bytes\":%" PRIu64 ",\"pico_base_ws_bytes\":%" PRIu64
               ",\"pico_ws_bytes\":%" PRIu64, (uint64_t)antes.WorkingSetSize,
               (uint64_t)antes.PeakWorkingSetSize, (uint64_t)depois.PeakWorkingSetSize);
    } else if (modo == AUXILIAR) {
        printf(",\"aux_c_heap_bytes\":%" PRIu64, (uint64_t)aux_heap);
    }
    puts("}");
    return 0;
}
