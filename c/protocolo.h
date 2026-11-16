#ifndef MOCHILA_PROTOCOLO_H
#define MOCHILA_PROTOCOLO_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint64_t peso;
    uint64_t valor;
} Item;

/* Retorna 0 em sucesso ou uma mensagem estática de erro. */
typedef const char *(*Solucionador)(const Item *, size_t, uint64_t, uint64_t *, size_t *);
int executar(int argc, char **argv, Solucionador resolver, uint64_t max_itens);

#endif
