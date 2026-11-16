#include "protocolo.h"

static const char *resolver(const Item *itens, size_t n, uint64_t capacidade,
                            uint64_t *otimo, size_t *aux_heap)
{
    uint64_t melhor = 0;
    const uint64_t total = UINT64_C(1) << n;
    for (uint64_t mascara = 0; mascara < total; ++mascara) {
        uint64_t bits = mascara;
        uint64_t peso_total = 0;
        uint64_t valor_total = 0;
        for (size_t i = 0; i < n; ++i) {
            if (bits & UINT64_C(1)) {
                peso_total += itens[i].peso;
                valor_total += itens[i].valor;
            }
            bits >>= 1;
        }
        if (peso_total <= capacidade && valor_total > melhor) {
            melhor = valor_total;
        }
    }
    *otimo = melhor;
    *aux_heap = 0;
    return NULL;
}

int main(int argc, char **argv)
{
    return executar(argc, argv, resolver, 62);
}
