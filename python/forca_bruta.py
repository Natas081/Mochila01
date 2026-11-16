"""Busca exaustiva por máscaras, sem poda."""

def resolver(itens, capacidade):
    """Recebe itens (peso, valor) já validados e devolve o valor ótimo."""
    melhor = 0
    for mascara in range(1 << len(itens)):
        bits = mascara
        peso_total = valor_total = 0
        for peso, valor in itens:
            if bits & 1:
                peso_total += peso
                valor_total += valor
            bits >>= 1
        if peso_total <= capacidade and valor_total > melhor:
            melhor = valor_total
    return melhor


if __name__ == "__main__":
    from protocolo import executar

    raise SystemExit(executar(resolver, max_itens=62))
