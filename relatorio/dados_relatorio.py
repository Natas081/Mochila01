"""Consulta dos resultados medidos para os materiais acadêmicos."""

import json

import pandas as pd

FB, PD = "forca_bruta", "programacao_dinamica"
PROGRAMAS = (("Python", FB), ("C", FB), ("Python", PD), ("C", PD))


def br(numero, casas=0):
    return f"{numero:,.{casas}f}".translate(str.maketrans(".,", ",."))


class Dados:
    def __init__(self, pasta):
        self.ambiente = json.loads((pasta / "ambiente.json").read_text(encoding="utf-8"))
        tabelas = pasta / "tabelas"
        self.tempos = pd.read_csv(tabelas / "tempo_resumo.csv")
        self.memoria = pd.read_csv(tabelas / "memoria_resumo.csv")
        self.piloto = pd.read_csv(tabelas / "piloto.csv")
        self.teoria = pd.read_csv(tabelas / "crescimento_teorico.csv")
        self.graficos = pasta / "graficos"

    def tempo(self, ident, ling, alg, campo="media"):
        dados = self.tempos
        selecao = dados["id"].eq(ident) & dados["linguagem"].eq(ling) & dados["algoritmo"].eq(alg)
        return dados.loc[selecao, campo].item()

    def mem(self, ident, ling, alg, metrica):
        dados = self.memoria
        selecao = (dados["id"].eq(ident) & dados["linguagem"].eq(ling) &
                   dados["algoritmo"].eq(alg) & dados["metrica"].eq(metrica))
        return dados.loc[selecao, "media"].item()

    def limites(self, ling):
        grupo = self.piloto[self.piloto["linguagem"] == ling]
        viavel = grupo[grupo["status"] == "viavel"].sort_values("n").iloc[-1]
        inviavel = grupo[grupo["status"] != "viavel"].sort_values("n").iloc[0]
        return viavel, inviavel
