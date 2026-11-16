"""Tabulação bidimensional da mochila 0/1."""

def resolver(itens, capacidade):
    """Recebe itens (peso, valor) já validados e devolve o valor ótimo."""
    tabela = [[0] * (capacidade + 1) for _ in range(len(itens) + 1)]
    for i, (peso, valor) in enumerate(itens, start=1):
        anterior, atual = tabela[i - 1], tabela[i]
        for limite in range(capacidade + 1):
            melhor = anterior[limite]
            if peso <= limite:
                com_item = valor + anterior[limite - peso]
                if com_item > melhor:
                    melhor = com_item
            atual[limite] = melhor
    return tabela[-1][capacidade]


if __name__ == "__main__":
    from protocolo import executar

    raise SystemExit(executar(resolver))
