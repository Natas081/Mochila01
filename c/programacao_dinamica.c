#include "protocolo.h"

#include <stdlib.h>

static const char *resolver(const Item *itens, size_t n, uint64_t capacidade,
                            uint64_t *otimo, size_t *aux_heap)
{
    if (capacidade >= SIZE_MAX || n == SIZE_MAX) {
        return "dimensoes da tabela acima do limite da plataforma";
    }
    const size_t colunas = (size_t)capacidade + 1;
    if ((n + 1) > (SIZE_MAX / sizeof(uint64_t)) / colunas) {
        return "tabela grande demais para o espaco de enderecamento";
    }
    const size_t celulas = (n + 1) * colunas;
    uint64_t *tabela = calloc(celulas, sizeof *tabela);
    if (tabela == NULL) {
        return "memoria insuficiente para a tabela";
    }

    for (size_t i = 1; i <= n; ++i) {
        uint64_t *anterior = tabela + (i - 1) * colunas;
        uint64_t *atual = anterior + colunas;
        const Item item = itens[i - 1];
        for (size_t limite = 0; limite < colunas; ++limite) {
            uint64_t melhor = anterior[limite];
            if (item.peso <= limite) {
                uint64_t com_item = item.valor + anterior[limite - (size_t)item.peso];
                if (com_item > melhor) {
                    melhor = com_item;
                }
            }
            atual[limite] = melhor;
        }
    }

    *otimo = tabela[celulas - 1];
    *aux_heap = celulas * sizeof *tabela;
    free(tabela);
    return NULL;
}

int main(int argc, char **argv)
{
    return executar(argc, argv, resolver, INT64_MAX);
}
