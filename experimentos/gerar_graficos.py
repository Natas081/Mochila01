"""Audita os CSV brutos, calcula estatísticas e gera figuras do estudo."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from experimentos.comum import PROGRAMAS, RAIZ
from experimentos.gerar_entradas import PASTA_DADOS

FB, PD = "forca_bruta", "programacao_dinamica"
ESTILOS = {
    ("Python", FB): ("#974120", "o"), ("C", FB): ("#b5770f", "s"),
    ("Python", PD): ("#245891", "D"), ("C", PD): ("#087568", "^"),
}
ROTULOS = {FB: "Força bruta", PD: "Programação dinâmica"}
GRUPOS = ["id", "serie", "n", "W", "linguagem", "algoritmo"]
METRICAS_WS = ["base_ws_bytes", "pico_base_ws_bytes", "pico_ws_bytes", "aumento_pico_ws_bytes"]


def exigir(condicao, erro):
    if not condicao:
        raise ValueError(erro)


def auditar(pasta):
    ambiente = json.loads((pasta / "ambiente.json").read_text(encoding="utf-8"))
    manifesto_bytes = (PASTA_DADOS / "manifesto.json").read_bytes()
    exigir(hashlib.sha256(manifesto_bytes).hexdigest() == ambiente["manifesto_sha256"],
           "O manifesto difere do registrado na coleta.")
    manifesto = json.loads(manifesto_bytes)
    for instancia in manifesto:
        entrada = (PASTA_DADOS / instancia["arquivo"]).read_bytes()
        exigir(hashlib.sha256(entrada).hexdigest() == instancia["sha256"],
               f"Os bytes da entrada foram alterados: {instancia['id']}.")
    instancias = {i["id"]: i for i in manifesto if i["serie"] != "piloto"}
    tempo = pd.read_csv(pasta / "tabelas" / "tempo_bruto.csv")
    memoria = pd.read_csv(pasta / "tabelas" / "memoria_bruta.csv")
    piloto = pd.read_csv(pasta / "tabelas" / "piloto.csv")

    for dados, nome in ((tempo, "tempo"), (memoria, "memoria")):
        reps = ambiente[f"repeticoes_{nome}"]
        esperado = {(ident, rep, ling, alg) for ident in instancias
                    for rep in range(1, reps + 1) for ling, alg in PROGRAMAS}
        observado = list(dados[["id", "repeticao", "linguagem", "algoritmo"]]
                         .itertuples(index=False, name=None))
        exigir(set(observado) == esperado and len(observado) == len(esperado),
               f"Cobertura incompleta ou linhas duplicadas em {nome}.")
        for ident, bloco in dados.groupby("id"):
            for campo in ("serie", "n", "W", "sha256"):
                exigir(bloco[campo].eq(instancias[ident][campo]).all(),
                       f"Instância divergente em {nome}: {ident}, {campo}")
            exigir(bloco["otimo"].nunique() == 1 and bloco["otimo"].ge(0).all(),
                   f"Ótimo inconsistente em {nome}: {ident}")
            for _, repeticao in bloco.groupby("repeticao"):
                exigir(set(repeticao["ordem"]) == {1, 2, 3, 4},
                       f"Ordem inválida em {nome}: {ident}")
    exigir(tempo["tempo_ns"].gt(0).all(), "Tempo igual ou inferior a zero.")
    exigir(tempo.groupby("id")["otimo"].first().equals(memoria.groupby("id")["otimo"].first()),
           "Ótimos divergem entre tempo e memória.")
    exigir((memoria["base_ws_bytes"].gt(0) &
            memoria["pico_base_ws_bytes"].ge(memoria["base_ws_bytes"]) &
            memoria["pico_ws_bytes"].ge(memoria["pico_base_ws_bytes"])).all(),
           "Contadores de working set inválidos.")
    python = memoria[memoria["linguagem"] == "Python"]
    c = memoria[memoria["linguagem"] == "C"]
    esperado_c = np.where(c["algoritmo"].eq(PD), 8 * (c["n"] + 1) * (c["W"] + 1), 0)
    exigir(python["aux_py_bytes"].ge(0).all() and python["aux_c_heap_bytes"].isna().all(),
           "Colunas auxiliares inválidas em Python.")
    exigir(c["aux_c_heap_bytes"].eq(esperado_c).all() and c["aux_py_bytes"].isna().all(),
           "Colunas auxiliares inválidas em C.")

    por_id = {i["id"]: i for i in manifesto if i["serie"] == "piloto"}
    exigir(set(piloto["linguagem"]) == {"Python", "C"} and
           not piloto.duplicated(["id", "linguagem"]).any(), "Identidades inválidas no piloto.")
    comparacao_piloto = {}
    for ling, grupo in piloto.groupby("linguagem"):
        for linha in grupo.itertuples():
            exigir(all(getattr(linha, chave) == por_id[linha.id][chave]
                       for chave in ("serie", "n", "W", "sha256")), "Entrada do piloto inválida.")
            if linha.status == "timeout":
                exigir(pd.isna(linha.tempo_ns) and pd.isna(linha.otimo), "Timeout com saída medida.")
            else:
                status = "viavel" if linha.tempo_ns <= ambiente["limite_piloto_s"] * 1e9 else "acima_limite"
                exigir(linha.status == status and linha.tempo_ns > 0 and
                       linha.otimo == linha.otimo_pd, "Ótimo, tempo ou status inválido no piloto.")
            anterior = comparacao_piloto.setdefault(linha.n, linha.otimo_pd)
            exigir(anterior == linha.otimo_pd, "Ótimo de referência divergente no piloto.")
        viavel = grupo[grupo["status"] == "viavel"]
        inviavel = grupo[grupo["status"] != "viavel"]
        exigir(not viavel.empty and not inviavel.empty and
               viavel["n"].max() + 1 == inviavel["n"].min(), f"Piloto incompleto em {ling}.")
    return tempo, memoria, piloto


def resumo(dados, coluna):
    grupo = dados.groupby(GRUPOS)[coluna].agg(
        amostras="count", media="mean", dp="std", minimo="min", maximo="max",
    ).reset_index()
    return grupo[grupo["amostras"].gt(0)]


def salvar(fig, pasta, nome):
    fig.savefig(pasta / (nome + ".png"), dpi=240, facecolor="white")
    plt.close(fig)


def base(titulo, largura=7.4, altura=4.1):
    fig, ax = plt.subplots(figsize=(largura, altura), layout="constrained")
    ax.set_title(titulo, loc="left", fontweight="bold", pad=13)
    return fig, ax


def rotulo(linguagem, algoritmo):
    return f"{ROTULOS[algoritmo]} · {linguagem}"


def eixos(ax, x, y, ticks=None):
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    if ticks is not None:
        ax.set_xticks(ticks)
    ax.grid(axis="y", which="major", alpha=0.24)
    ax.spines[["top", "right"]].set_visible(False)


def curvas(ax, dados, programas, x, divisor=1, log=False):
    for ling, alg in programas:
        fatia = dados[(dados["linguagem"] == ling) & (dados["algoritmo"] == alg)].sort_values(x)
        cor, marcador = ESTILOS[ling, alg]
        ax.errorbar(fatia[x], fatia["media"]/divisor, yerr=fatia["dp"]/divisor,
                    color=cor, marker=marcador, linewidth=1.6, markersize=5,
                    alpha=0.94, capsize=2.5, label=rotulo(ling, alg))
    if log:
        ax.set_yscale("log")
    ax.legend(frameon=False, fontsize=8, ncols=2 if len(programas) == 4 else 1)


def graficos_tempo(tempo, pasta):
    dados = tempo[tempo["serie"] == "principal"]
    ns = sorted(dados["n"].unique())
    referencia = ns[len(ns) // 2]
    for nome, titulo, programas in (
        ("01_tempo_forca_bruta", "Tempo da força bruta", PROGRAMAS[:2]),
        ("02_tempo_programacao_dinamica", "Tempo da programação dinâmica", PROGRAMAS[2:]),
        ("03_tempo_python", "Mochila 0/1 em Python", PROGRAMAS[::2]),
        ("04_tempo_c", "Mochila 0/1 em C", PROGRAMAS[1::2]),
        ("05_tempo_quatro_programas", "Tempo dos quatro programas", PROGRAMAS),
    ):
        fig, ax = base(titulo)
        curvas(ax, dados, programas, "n", 1e3, log=True)
        eixos(ax, "Número de itens (n)", "Tempo médio (µs, escala log)", ns)
        salvar(fig, pasta, nome)

    for comparar, nome, titulo in (
        (True, "06_tempo_e_teoria", "Crescimento observado e previsto"),
        (False, "07_razao_tempo_trabalho", "Tempo médio por unidade de trabalho"),
    ):
        fig, axes = plt.subplots(1, 2, figsize=(10.8, 4), layout="constrained")
        fig.suptitle(titulo, fontweight="bold", fontsize=14)
        for ax, alg in zip(axes, (FB, PD)):
            dados_alg = dados[dados["algoritmo"] == alg].copy()
            base_teorica = dados_alg.drop_duplicates("n").set_index("n").sort_index()
            trabalho = (base_teorica.index * 2**base_teorica.index if alg == FB
                        else base_teorica.index * (base_teorica["W"] + 1))
            modelo = pd.Series(np.asarray(trabalho, dtype=float), index=base_teorica.index)
            formula = "n × 2ⁿ" if alg == FB else "n × (W+1)"
            ax.set_title(f"{ROTULOS[alg]}  /  {formula}", fontsize=11)
            if comparar:
                for ling in ("Python", "C"):
                    selecao = dados_alg["linguagem"] == ling
                    ancora = dados_alg.loc[selecao & dados_alg["n"].eq(referencia), "media"].item()
                    dados_alg.loc[selecao, ["media", "dp"]] /= ancora
                ax.plot(ns, modelo / modelo.loc[referencia], "--", color="#555b61",
                        linewidth=1.15, label="Modelo teórico")
                y = f"T(n) / T({referencia}), escala log"
            else:
                dados_alg[["media", "dp"]] = dados_alg[["media", "dp"]].div(
                    dados_alg["n"].map(modelo), axis=0)
                y = "Razão (ns por unidade, escala log)"
            pares = [(ling, alg) for ling in ("Python", "C")]
            curvas(ax, dados_alg, pares, "n", log=True)
            eixos(ax, "Número de itens (n)", y, ns)
        salvar(fig, pasta, nome)


def formatar_w(x, _):
    return f"{x:,.0f}".replace(",", ".")


def graficos_memoria(resultados, pasta):
    processo = resultados["pico_ws_bytes"]
    principal = processo[processo["serie"] == "principal"]
    ns = sorted(principal["n"].unique())
    fig, ax = base("Pico do working set por programa")
    curvas(ax, principal, PROGRAMAS, "n", 2**20)
    ax.set_ylim(bottom=0)
    eixos(ax, "Número de itens (n)", "Pico médio do processo (MiB)", ns)
    salvar(fig, pasta, "08_memoria_processo")

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4), layout="constrained")
    fig.suptitle("Memória auxiliar por linguagem", fontweight="bold", fontsize=14)
    for ax, ling, metrica, titulo in (
        (axes[0], "Python", "aux_py_bytes", "Python · pico rastreado com tracemalloc"),
        (axes[1], "C", "aux_c_heap_bytes", "C · bytes solicitados no heap"),
    ):
        dados = resultados[metrica]
        ax.set_title(titulo, fontsize=11)
        curvas(ax, dados[dados["serie"] == "principal"], [(ling, alg) for alg in (FB, PD)], "n", 1024)
        ax.set_yscale("symlog", linthresh=1)
        ax.set_ylim(bottom=0)
        eixos(ax, "Número de itens (n)", "Média (KiB, escala symlog)", ns)
    salvar(fig, pasta, "09_memoria_auxiliar")

    fig, axes = plt.subplots(1, 3, figsize=(12.9, 4), layout="constrained")
    fig.suptitle("Memória da tabulação com 12 itens e capacidade variável", fontweight="bold", fontsize=14)
    for ax, metrica, idiomas, titulo, y, divisor in (
        (axes[0], "pico_ws_bytes", ("Python", "C"), "Processo", "Pico médio (MiB)", 2**20),
        (axes[1], "aux_py_bytes", ("Python",), "Python · tracemalloc", "Pico médio (KiB)", 1024),
        (axes[2], "aux_c_heap_bytes", ("C",), "C · heap solicitado", "Média (KiB)", 1024),
    ):
        dados = resultados[metrica]
        dados = dados[dados["serie"].eq("capacidade")]
        ax.set_title(titulo, fontsize=11)
        curvas(ax, dados, [(ling, PD) for ling in idiomas], "W", divisor)
        ax.set_xscale("symlog", linthresh=120)
        ax.set_ylim(bottom=0)
        eixos(ax, "Capacidade (W)", y, (0, 240, 2400, 24000))
        ax.xaxis.set_major_formatter(FuncFormatter(formatar_w))
    salvar(fig, pasta, "10_memoria_capacidade")


def graficos_auxiliares(tempo, pasta):
    fig, ax = base("Perfis de peso com 12 itens e capacidade 240")
    perfis = tempo[tempo["serie"].eq("perfil") | tempo["id"].eq("capacidade_w00240")].copy()
    perfis["perfil"] = perfis["id"].map({"peso_excessivo": 0, "capacidade_w00240": 1, "peso_zero": 2})
    curvas(ax, perfis, PROGRAMAS, "perfil", 1e3, log=True)
    ax.get_legend().set_loc("upper center")
    ax.get_legend().set_bbox_to_anchor((0.5, -0.23))
    eixos(ax, "Perfil dos pesos", "Tempo médio (µs, escala log)", range(3))
    ax.set_xticklabels(["Todos excedem W", "Pesos aleatórios", "Todos zero"])
    salvar(fig, pasta, "11_tempo_perfis")

    fig, ax = base("Tempo com 12 itens e capacidade variável")
    capacidade = tempo[tempo["serie"].eq("capacidade")]
    curvas(ax, capacidade, PROGRAMAS, "W", 1e3, log=True)
    ax.set_xscale("symlog", linthresh=120)
    eixos(ax, "Capacidade (W)", "Tempo médio (µs, escala log)", (0, 240, 2400, 24000))
    ax.xaxis.set_major_formatter(FuncFormatter(formatar_w))
    salvar(fig, pasta, "12_tempo_capacidade")


def gerar(pasta):
    tempo, memoria, piloto = auditar(pasta)
    print(f"Cobertura e consistência conferidas em {len(tempo)} tempos, "
          f"{len(memoria)} pares de memória e {len(piloto)} tentativas do piloto.")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.labelpad": 7})
    graficos = pasta / "graficos"
    graficos.mkdir(exist_ok=True)
    tabelas = pasta / "tabelas"
    tempos = resumo(tempo, "tempo_ns")
    tempos.to_csv(tabelas / "tempo_resumo.csv", index=False)
    memoria["aumento_pico_ws_bytes"] = memoria["pico_ws_bytes"] - memoria["pico_base_ws_bytes"]
    metricas = [*METRICAS_WS, "aux_py_bytes", "aux_c_heap_bytes"]
    resultados = {metrica: resumo(memoria, metrica) for metrica in metricas}
    pd.concat([dados.assign(metrica=metrica) for metrica, dados in resultados.items()],
              ignore_index=True).to_csv(tabelas / "memoria_resumo.csv", index=False)
    teorico = tempos[tempos["serie"] == "principal"].copy()
    teorico["trabalho"] = np.where(teorico["algoritmo"].eq(FB), teorico["n"] * 2**teorico["n"],
                                  teorico["n"] * (teorico["W"] + 1))
    teorico["media_ns_por_unidade"] = teorico["media"] / teorico["trabalho"]
    teorico.to_csv(tabelas / "crescimento_teorico.csv", index=False)
    graficos_tempo(tempos, graficos)
    graficos_memoria(resultados, graficos)
    graficos_auxiliares(tempos, graficos)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=RAIZ / "resultados")
    gerar(parser.parse_args().saida)
