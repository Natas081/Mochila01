"""Gera o relatório acadêmico a partir dos CSV e PNG da coleta."""

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from PIL import Image as LeitorImagem
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

from experimentos.comum import RAIZ
from relatorio.dados_relatorio import Dados, FB, PD, PROGRAMAS, br

MARINHO = "#14283C"
VERDE = "#087568"
TEXTO = "#26394B"
CINZA = "#526479"
CLARO = "#EFF4F5"
BORDA = "#CDD9DF"
LARGURA = A4[0] - 104
NOMES = {FB: "Força bruta", PD: "Programação dinâmica"}
REFERENCIAS = [
    ("MIT OPENCOURSEWARE. Dynamic Programming: Knapsack Problem. "
     "Introduction to Algorithms, 6.006, 2011.",
     "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/95e744ee64464cb6bc8f8264faeea080_MIT6_006F11_rec21.pdf"),
    ("WAYNE, Kevin. Intractability I. Slides complementares a KLEINBERG, Jon e TARDOS, Éva. "
     "Algorithm Design. Pearson, 2005. Redução de Subset Sum à Mochila.",
     "https://www.cs.princeton.edu/~wayne/kleinberg-tardos/pdf/08IntractabilityI.pdf"),
    ("ROUGHGARDEN, Tim. Lecture 4: Algorithmic Mechanism Design. CS364A, Stanford University, 2013. § 2.2.",
     "https://theory.stanford.edu/~tim/f13/l/l4.pdf"),
    ("PYTHON SOFTWARE FOUNDATION. time e tracemalloc. Documentação do Python 3.13.",
     "https://docs.python.org/3.13/library/time.html#time.perf_counter_ns",
     "https://docs.python.org/3.13/library/tracemalloc.html"),
    ("MICROSOFT. QueryPerformanceCounter. Windows API.",
     "https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter"),
    ("MICROSOFT. Process Memory Usage Information. Windows API.",
     "https://learn.microsoft.com/en-us/windows/win32/psapi/process-memory-usage-information"),
]


def preparar_fontes():
    pasta = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for nome, arquivo in (("Texto", "DejaVuSans"), ("Texto-Bold", "DejaVuSans-Bold"),
                          ("Texto-Italic", "DejaVuSans-Oblique"), ("Codigo", "DejaVuSansMono")):
        pdfmetrics.registerFont(TTFont(nome, str(pasta / f"{arquivo}.ttf")))
    pdfmetrics.registerFontFamily("Texto", normal="Texto", bold="Texto-Bold",
                                  italic="Texto-Italic", boldItalic="Texto-Bold")


def moldura(canvas, doc):
    largura, altura = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(BORDA))
    canvas.line(52, 47, largura - 52, 47)
    canvas.setFillColor(colors.HexColor(CINZA))
    canvas.setFont("Texto", 8)
    canvas.drawString(52, 32, "Teoria da Computação   /   Mochila 0/1")
    canvas.drawRightString(largura - 52, 32, str(doc.page))
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor(VERDE))
        canvas.setLineWidth(2)
        canvas.line(52, altura - 39, largura - 52, altura - 39)
    canvas.restoreState()


class Relatorio:
    def __init__(self, dados):
        self.dados = dados
        self.partes = []
        self.estilos = {
            "texto": ParagraphStyle("texto", fontName="Texto", fontSize=10.3, leading=15.2,
                                    spaceAfter=8, textColor=colors.HexColor(TEXTO)),
            "titulo": ParagraphStyle("titulo", fontName="Texto-Bold", fontSize=18, leading=23,
                                     spaceAfter=13, textColor=colors.HexColor(MARINHO)),
            "sub": ParagraphStyle("sub", fontName="Texto-Bold", fontSize=12, leading=16,
                                  spaceBefore=6, spaceAfter=6, textColor=colors.HexColor(VERDE)),
            "legenda": ParagraphStyle("legenda", fontName="Texto", fontSize=8.2, leading=11.5,
                                      spaceAfter=9, textColor=colors.HexColor(CINZA)),
            "celula": ParagraphStyle("celula", fontName="Texto", fontSize=8, leading=11,
                                     textColor=colors.HexColor(TEXTO)),
            "numerica": ParagraphStyle("numerica", fontName="Texto", fontSize=8, leading=11,
                                       alignment=TA_RIGHT, textColor=colors.HexColor(TEXTO)),
            "cabecalho": ParagraphStyle("cabecalho", fontName="Texto-Bold", fontSize=8, leading=11,
                                        alignment=TA_CENTER, textColor=colors.white),
            "capa": ParagraphStyle("capa", fontName="Texto-Bold", fontSize=37, leading=43,
                                   spaceAfter=15, textColor=colors.HexColor(MARINHO)),
            "resumo": ParagraphStyle("resumo", fontName="Texto", fontSize=12, leading=18,
                                     spaceAfter=8, textColor=colors.HexColor(TEXTO)),
        }

    def p(self, texto, estilo="texto"):
        self.partes.append(Paragraph(texto, self.estilos[estilo]))

    def pagina(self, titulo):
        self.partes.append(PageBreak())
        self.p(titulo, "titulo")

    def codigo(self, texto):
        estilo = ParagraphStyle("codigo", fontName="Codigo", fontSize=8.8, leading=12.4,
                                textColor=colors.HexColor(MARINHO))
        self.partes.extend([
            Table([[Preformatted(texto, estilo)]], colWidths=[LARGURA - 12], style=[
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(CLARO)),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ], hAlign="LEFT"),
            Spacer(1, 8),
        ])

    def tabela(self, linhas, larguras, legenda, numericas=()):
        celulas = [
            [Paragraph(escape(str(x)), self.estilos["cabecalho" if i == 0 else
                        "numerica" if j in numericas else "celula"])
             for j, x in enumerate(linha)]
            for i, linha in enumerate(linhas)
        ]
        tabela = Table(celulas, colWidths=larguras, repeatRows=1, hAlign="LEFT")
        tabela.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MARINHO)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(CLARO), colors.white]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor(BORDA)),
        ]))
        self.partes.append(KeepTogether([
            tabela, Spacer(1, 5), Paragraph(legenda, self.estilos["legenda"]),
        ]))

    def imagem(self, nome, largura):
        caminho = self.dados.graficos / f"{nome}.png"
        with LeitorImagem.open(caminho) as imagem:
            w, h = imagem.size
        return Image(str(caminho), width=largura, height=largura*h/w)

    def figura(self, nome, legenda, largura=LARGURA - 14):
        grafico = self.imagem(nome, largura)
        grafico.hAlign = "CENTER"
        self.partes.append(KeepTogether([
            grafico, Spacer(1, 4), Paragraph(legenda, self.estilos["legenda"]),
        ]))

    def capa(self, equipe):
        self.partes.append(Spacer(1, 62))
        if equipe["instituicao"]:
            self.p(escape(equipe["instituicao"]), "sub")
        self.p("Mochila 0/1", "capa")
        self.p("Análise de tempo e memória da força bruta e da programação dinâmica em Python e C",
               "resumo")
        self.partes.append(Spacer(1, 20))
        self.p(f"<b>{escape(equipe['disciplina'])}</b><br/>Docente · {escape(equipe['docente'])}")
        self.p("<br/>".join(escape(e["nome"]) for e in equipe["integrantes"]))
        self.partes.append(Spacer(1, 32))
        self.p("Resumo", "sub")
        py, _ = self.dados.limites("Python")
        c, _ = self.dados.limites("C")
        self.p("Quatro programas resolvem as mesmas instâncias da Mochila 0/1. Comparamos "
               "os tempos em seis tamanhos com 20 execuções por programa e por instância. "
               f"No piloto de 60 s, a enumeração concluiu até {int(py.n)} itens em Python "
               f"e {int(c.n)} em C. A tabulação cresceu com a capacidade, tanto no tempo "
               "quanto na memória auxiliar. Os quatro programas concordaram sobre o valor "
               "ótimo em toda a coleta pareada.")
        self.p("<b>Palavras-chave</b> · Mochila 0/1, programação dinâmica, análise de algoritmos, NP-completude.")

    def algoritmos(self):
        self.pagina("1  Descrição do problema e dos algoritmos")
        self.p("Cada item <i>i</i> tem peso inteiro <i>wᵢ</i> ≥ 0 e valor inteiro <i>vᵢ</i> ≥ 0. "
               "Dada a capacidade inteira <i>W</i> ≥ 0, escolhemos <i>xᵢ</i> ∈ {0, 1} "
               "para maximizar Σ <i>vᵢxᵢ</i>, sujeito a Σ <i>wᵢxᵢ</i> ≤ <i>W</i>. "
               "Cada programa retorna o valor máximo. Por exemplo, para os pares "
               "(10, 60), (20, 100), (30, 120) e <i>W</i> = 50, os dois últimos itens "
               "somam peso 50 e valor ótimo 220.")
        self.p("Força bruta iterativa", "sub")
        self.p("Os <i>n</i> bits de uma máscara representam as decisões de inclusão, em "
               "bijeção com os subconjuntos. O laço examina todos os bits, inclusive "
               "quando o peso já excede a capacidade. Após cada máscara, melhor guarda "
               "o maior valor viável já encontrado. Ao fim, a enumeração exibiu todas as opções.")
        self.codigo("""melhor ← 0
para máscara de 0 até 2ⁿ - 1:
    peso ← 0, valor ← 0, bits ← máscara
    para cada item (w, v), na ordem:
        se bits & 1: peso ← peso + w, valor ← valor + v
        bits ← bits deslocados 1 posição à direita
    se peso ≤ W: melhor ← máximo(melhor, valor)
retorne melhor""")
        self.p("Programação dinâmica por tabulação", "sub")
        self.p("D[i, c] é o maior valor com os primeiros <i>i</i> itens e capacidade <i>c</i>. "
               "Sem o item <i>i</i>, o valor é D[i-1, c]. Se o item couber, somamos seu valor "
               "ao melhor subconjunto dos itens anteriores que cabe no espaço restante. "
               "As duas opções cobrem todos os subconjuntos. A linha anterior garante "
               "o uso de cada item uma única vez, inclusive se seu peso for zero. [1, 2]")
        self.codigo("""alocar D[0..n, 0..W] com zeros
para i de 1 até n:
    para c de 0 até W:
        D[i,c] ← D[i-1,c]
        se w[i] ≤ c:
            D[i,c] ← máximo(D[i,c], v[i] + D[i-1,c-w[i]])
retorne D[n,W]""")
        self.p("A linha 0 representa o conjunto vazio. Na coluna 0, apenas os itens de "
               "peso zero podem contribuir. A regra também resolve a instância com <i>n</i> = 0.")

    def complexidade(self):
        self.pagina("2  Classificação assintótica")
        self.p("Consideramos um modelo de custo unitário para palavras que comportam "
               "máscaras, índices e somas. As interfaces usam somas de até 2⁶³ − 1 "
               "e limitam a enumeração a 62 bits. No modelo de bits com máscaras "
               "de largura variável, a máscara ocupa Θ(n) bits e operações sobre "
               "inteiros longos podem ter custo adicional.")
        self.tabela([
            ["Algoritmo", "Tempo", "Memória auxiliar"],
            ["Força bruta", "Θ(1 + n · 2ⁿ)", "Θ(1) palavras no modelo adotado"],
            ["Programação dinâmica", "Θ((n+1)(W+1))", "Θ((n+1)(W+1)) posições"],
        ], [140, 163, 170], "Tabela 1. Limites justos das implementações. A entrada ocupa Θ(n) palavras.")
        self.p("<b>Enumeração.</b> Há exatamente 2ⁿ máscaras e <i>n</i> testes de bit por "
               "máscara. Para <i>n</i> ≥ 1, os blocos de custo constante dão O(n · 2ⁿ), "
               "e a visita a todos os bits exige Ω(n · 2ⁿ). Juntos, os limites dão "
               "Θ(n · 2ⁿ). A implementação mantém um número constante de contadores, "
               "máscaras e acumuladores simultaneamente. A instância vazia custa Θ(1).")
        self.p("<b>Tabulação.</b> A tabela tem (n+1)(W+1) posições, e há n(W+1) "
               "atualizações com até uma adição e uma comparação extra. Para <i>n</i> ≥ 1, "
               "essas atualizações garantem Ω(n(W+1)) e a alocação e os laços custam "
               "O((n+1)(W+1)). Para <i>W</i> ≥ 1, obtemos Θ(nW) em tempo e espaço. "
               "Quando W = 0, construímos uma coluna e visitamos n posições. "
               "Quando n = 0, apenas a linha base é alocada. Em C, a reserva zerada "
               "dessa linha pode usar inicialização preguiçosa do alocador. A contagem "
               "assintótica toma o custo usual de armazenamento e inicialização da tabela.")
        self.p("3  Melhor, pior e caso médio", "titulo")
        self.p("Para dimensões fixas, as contagens de máscaras e de células permanecem "
               "iguais em todas as entradas. Portanto, a ordem Θ do melhor caso, do pior "
               "e da esperança sobre qualquer distribuição nessas dimensões é a mesma. "
               "Ramos de viabilidade, atualizações do máximo, alocação e previsibilidade "
               "dos desvios podem alterar o custo por iteração. A média de 20 repetições "
               "estima o tempo de uma instância específica sob variação de execução.")
        self.p("4  Aplicabilidade prática", "titulo")
        self.p("A força bruta serve como referência exata em conjuntos pequenos, inclusive "
               "com capacidades numéricas grandes. A tabulação atende problemas com muitas "
               "combinações e capacidade discreta moderada, como seleção de projetos com "
               "orçamento inteiro. A tabela completa limita o método quando W é grande. "
               "Uma linha percorrida da maior capacidade para a menor pode reduzir o "
               "espaço para Θ(W+1), preservando o valor ótimo em outra implementação.")

    def metodologia(self):
        self.pagina("5  Simulação e metodologia experimental")
        a = self.dados.ambiente
        self.p("Antes da coleta, os quatro executáveis passaram por 12 casos conhecidos, "
               "26 casos aleatórios com referência independente, 15 entradas inválidas e "
               "verificações dos medidores. Cada bloco da coleta compara os ótimos e só "
               "persiste resultados se todos os programas concordarem.")
        self.p("Instâncias e repetições", "sub")
        self.p("A série principal usa n = 4, 6, 8, 11, 15 e 20 e W = 20n. Os seis n são os "
               "inteiros mais próximos de 4 × 1,38ᵏ, com k de 0 a 5. A razão foi escolhida "
               "para manter a série repetida até 20 itens e avaliar separadamente, no piloto, "
               "tamanhos próximos do limiar de 60 s. Os pesos são uniformes inteiros em [1, 50] "
               "e os valores em [1, 100], com semente 20261116 + n. Com 12 itens, variamos "
               "W entre 0, 240, 2.400 e 24.000. Em outros dois perfis, mantemos W = 240 e os "
               "valores, com pesos todos iguais a 0 ou a 241. O manifesto guarda a semente "
               "e o hash de cada entrada.")
        self.p("Cronometragem e piloto", "sub")
        self.p("A coleta em série usa 20 blocos por instância. Cada bloco embaralha a ordem "
               "dos quatro executáveis com semente fixa. Medimos somente a chamada ao "
               "solucionador, incluindo alocação e liberação da tabela. Inicialização, "
               "leitura, validação, geração e impressão ficam fora do intervalo. "
               "Usamos perf_counter_ns() em Python e QueryPerformanceCounter em C. "
               "O resultado calculado é consumido na saída JSON. O CPython usado aqui "
               "executou sem JIT e o código C foi compilado antes da coleta. [4, 5]")
        self.p("O piloto parte de n = 20 em cada linguagem e usa n · 2ⁿ para projetar "
               "passos de até quatro itens. Se necessário, refina o intervalo até obter "
               "tamanhos adjacentes. O limite do relógio interno é 60 s. O watchdog de "
               "62 s de parede dá margem à inicialização e à saída. Ao encerrá-lo, a "
               "observação fica censurada e o campo de tempo, vazio. Duas tabulações "
               "independentes conferem o ótimo de cada instância do piloto.")
        self.p("Memória", "sub")
        self.p("Três pares de execuções por instância e programa registram o working set "
               "e, em outro processo, a métrica auxiliar. Isso mantém a sobrecarga do "
               "tracemalloc fora da cronometragem e da comparação da memória residente. "
               "Usamos média, desvio-padrão amostral, mínimo e máximo.")
        self.tabela([
            ["Componente", "Ambiente registrado"],
            ["Sistema", f"{a['sistema']} · {a['versao_sistema']} · {a['arquitetura_host']}"],
            ["Processador e RAM", f"{a['cpu']} · {br(a['ram_bytes']/2**30, 2)} GiB"],
            ["Python", f"CPython {a['python'].split()[0]} · {a['python_bits']} bits"],
            ["GCC", f"{a['gcc']} · alvo {a['alvo_gcc']}"],
            ["Compilação", " ".join(a["flags_c"])],
        ], [122, 351], "Tabela 2. O arquivo ambiente.json registra as versões e os parâmetros da coleta.")

    def tempos(self):
        self.pagina("6  Resultados de tempo")
        d = self.dados
        linhas = [["n", "W", "Força bruta / Python", "Força bruta / C", "Tabulação / Python", "Tabulação / C"]]
        for n in d.ambiente["tamanhos"]:
            id = f"principal_n{n:02}"
            linhas.append([n, 20*n, *[
                f"{br(d.tempo(id, ling, alg)/1e3, 1)} ± {br(d.tempo(id, ling, alg, 'dp')/1e3, 1)}"
                for ling, alg in PROGRAMAS
            ]])
        self.tabela(linhas, [28, 30, 111, 107, 102, 95],
                    "Tabela 3. Média ± desvio-padrão amostral em µs. Mínimos e máximos nos CSV.",
                    numericas=range(6))
        self.figura("05_tempo_quatro_programas",
                    "Figura 1. Série principal em escala semilogarítmica. As barras registram "
                    "±1 desvio-padrão amostral das 20 execuções.")
        py_fb, c_fb, py_pd, c_pd = [d.tempo("principal_n20", ling, alg)/1e6
                                    for ling, alg in PROGRAMAS]
        self.p(f"Com 20 itens e W = 400, a força bruta levou {br(py_fb, 2)} ms em Python "
               f"e {br(c_fb, 2)} ms em C. A tabulação levou {br(py_pd, 3)} ms e "
               f"{br(c_pd, 3)} ms, respectivamente. A razão dos tempos de força bruta "
               f"para tabulação foi {br(py_fb/py_pd, 1)} em Python e {br(c_fb/c_pd, 1)} em C.")
        self.p("Os valores refletem estas implementações e este ambiente. A comparação "
               "inclui CPython de 64 bits e C de 32 bits compilado com otimização. "
               "Em chamadas muito curtas, resolução do relógio, estado da máquina "
               "e dispersão ganham importância. A média por ponto reflete uma única "
               "instância, e as cargas de fundo do sistema podem contribuir para a dispersão.")

    def crescimento(self):
        self.pagina("6  Crescimento observado e piloto")
        d = self.dados
        tamanhos = d.ambiente["tamanhos"]
        referencia = tamanhos[len(tamanhos) // 2]
        self.figura("06_tempo_e_teoria",
                    f"Figura 2. Medições e modelos divididos pelo respectivo valor em n = {referencia}. "
                    "Essa normalização compara a forma das curvas.")
        self.figura("07_razao_tempo_trabalho",
                    "Figura 3. Tempo dividido pelas visitas teóricas. Para W = 20n, a "
                    "tabulação cresce como Θ(n²) nesta série.")
        linhas = [["Linguagem", "Último n viável", "Tempo interno (s)", "Próximo n", "Resultado"]]
        for ling in ("Python", "C"):
            viavel, inviavel = d.limites(ling)
            estado = ("Timeout em 62 s" if inviavel.status == "timeout"
                      else f"{br(inviavel.tempo_ns/1e9, 2)} s internos")
            linhas.append([ling, int(viavel.n), br(viavel.tempo_ns/1e9, 2), int(inviavel.n), estado])
        self.tabela(linhas, [92, 87, 106, 72, 116],
                    "Tabela 4. Limite operacional observado da força bruta nas instâncias do piloto.",
                    numericas=(1, 2, 3))
        for alg, nome in NOMES.items():
            modelo = d.teoria[(d.teoria["algoritmo"] == alg) & (d.teoria["linguagem"] == "Python")]
            esperado = modelo.loc[modelo["n"].eq(20), "trabalho"].item() / modelo.loc[modelo["n"].eq(referencia), "trabalho"].item()
            p, c = [d.tempo("principal_n20", ling, alg)/d.tempo(f"principal_n{referencia:02}", ling, alg)
                    for ling in ("Python", "C")]
            self.p(f"<b>{nome}.</b> De {referencia} a 20 itens, o fator teórico foi {br(esperado, 2)}. "
                   f"Os fatores medidos foram {br(p, 2)} em Python e {br(c, 2)} em C.")
        self.p("Uma razão aproximadamente horizontal na Figura 3 é compatível com um custo "
               "estável por unidade de trabalho. A razão oscila com a instância, principalmente "
               "nos tempos curtos. O piloto usa uma tentativa por ponto e o ponto de corte "
               "pode mudar em outra sessão ou máquina.")

    def capacidade(self):
        self.pagina("6  Efeitos da capacidade e dos pesos")
        d = self.dados
        self.figura("11_tempo_perfis",
                    "Figura 4. Com n e W fixos, somente os pesos mudam entre os três perfis.", 421)
        self.figura("12_tempo_capacidade",
                    "Figura 5. Os 12 itens são idênticos. O eixo W usa escala linear perto de "
                    "zero e logarítmica para valores maiores.", 421)
        fatores = [d.tempo("peso_zero", ling, PD)/d.tempo("peso_excessivo", ling, PD)
                   for ling in ("Python", "C")]
        self.p(f"A razão entre os tempos da tabulação com pesos zero e com pesos acima de W "
               f"foi {br(fatores[0], 2)} em Python e {br(fatores[1], 2)} em C. "
               "O ramo que calcula o candidato incluído executa em todas as células "
               "de um perfil e em nenhuma do outro. As duas tabulações preenchem as mesmas "
               "dimensões. Na força bruta, cada máscara continua visitando os 12 itens.")
        fatores = [d.tempo("capacidade_w24000", ling, PD)/d.tempo("capacidade_w00240", ling, PD)
                   for ling in ("Python", "C")]
        self.p(f"De W = 240 para W = 24.000, os tempos da tabulação foram multiplicados por "
               f"{br(fatores[0], 1)} em Python e {br(fatores[1], 1)} em C. "
               "A força bruta mantém a contagem de máscaras ao mudar W. A capacidade "
               "influi na comparação de viabilidade e nas atualizações do ótimo.")
        tempos = [d.tempo("capacidade_w24000", ling, alg)/1e6 for ling, alg in PROGRAMAS]
        self.p(f"Em W = 24.000, a força bruta e a tabulação levaram {br(tempos[0], 2)} "
               f"e {br(tempos[2], 2)} ms em Python e {br(tempos[1], 3)} e "
               f"{br(tempos[3], 3)} ms em C, respectivamente.")

    def memoria(self):
        self.pagina("6  Análise de memória")
        d = self.dados
        self.figura("08_memoria_processo",
                    "Figura 6. Pico histórico do working set em processos iniciados para "
                    "esta medição. A base antes da chamada está no CSV.")
        self.figura("09_memoria_auxiliar",
                    "Figura 7. Métricas auxiliares por linguagem. A escala symlog representa "
                    "zero e comprime valores mais altos.")
        py, c = [d.mem("principal_n20", ling, FB, "pico_ws_bytes")/2**20 for ling in ("Python", "C")]
        self.p(f"Na força bruta com 20 itens, o pico médio do processo foi {br(py, 2)} MiB "
               f"em Python e {br(c, 2)} MiB em C. O working set inclui páginas residentes do "
               "interpretador, bibliotecas, entrada, pilha e alocador, inclusive páginas "
               "compartilhadas. Sua resolução em páginas e a variação do sistema dificultam "
               "isolar estruturas pequenas. O delta entre picos é somente o aumento do "
               "pico histórico entre as consultas. [6]")
        aux_py = d.mem("principal_n20", "Python", FB, "aux_py_bytes")
        self.p(f"Na força bruta com n = 20, o Python registrou {br(aux_py)} bytes "
               "rastreados em média e o C solicitou zero bytes de heap auxiliar. A pilha "
               "de C e os contadores ocupam espaço constante. A tabulação mantém uma "
               "tabela completa. Em Python, o rastreamento inclui listas, referências "
               "e inteiros temporários alocados na região medida. [4]")

        self.pagina("6  Memória da tabulação com W variável")
        self.figura("10_memoria_capacidade",
                    "Figura 8. Com 12 itens, o crescimento das colunas explica o aumento "
                    "da memória auxiliar. Cada painel indica sua métrica.")
        linhas = [["W", "Posições", "Pico Python (MiB)", "Pico C (MiB)",
                   "Rastreado Python (KiB)", "Heap C (KiB)"]]
        for w, id in ((0, "capacidade_w00000"), (240, "capacidade_w00240"),
                      (2400, "capacidade_w02400"), (24000, "capacidade_w24000")):
            linhas.append([br(w), br(13*(w+1)), *[
                br(d.mem(id, ling, PD, m)/unidade, 2) for ling, m, unidade in (
                    ("Python", "pico_ws_bytes", 2**20), ("C", "pico_ws_bytes", 2**20),
                    ("Python", "aux_py_bytes", 1024), ("C", "aux_c_heap_bytes", 1024),
                )
            ]])
        self.tabela(linhas, [54, 62, 88, 80, 105, 84],
                    "Tabela 5. Médias de três pares de execuções. 1 KiB = 1.024 bytes e 1 MiB = 1.024 KiB.",
                    numericas=range(6))
        self.p("Em C, o vetor contíguo armazena inteiros de 64 bits. Para W = 24.000, "
               "as 312.013 posições consomem 2.496.104 bytes de heap solicitado. "
               "Cada incremento unitário de W acrescenta 13 posições e 104 bytes no C.")
        py = d.mem("capacidade_w24000", "Python", PD, "aux_py_bytes")/1024
        self.p(f"No Python, o pico rastreado chegou a {br(py, 2)} KiB nesse ponto. "
               "A ocupação depende das referências da tabela, dos objetos inteiros "
               "gerados pelo ramo de inclusão e do compartilhamento de objetos entre "
               "células. A tendência acompanha as dimensões. Os valores de heap "
               "solicitado em C e de pico rastreado em Python têm escopos diferentes. "
               "As colunas de pico do processo usam a mesma métrica para as duas linguagens.")
        razao_celulas = 24001/2401
        razao_py = (d.mem("capacidade_w24000", "Python", PD, "aux_py_bytes") /
                    d.mem("capacidade_w02400", "Python", PD, "aux_py_bytes"))
        self.p(f"De W = 2.400 a W = 24.000, a tabela cresceu {br(razao_celulas, 2)} vezes. "
               "O heap auxiliar de C cresceu pelo mesmo fator, com 8 bytes por posição. "
               f"O pico rastreado em Python cresceu {br(razao_py, 2)} vezes. "
               "Na série principal, W = 20n implica Θ(n²) posições para a tabulação.")

    def teoria(self):
        self.pagina("7  Reflexão sobre P e NP")
        self.p("<b>P</b> reúne os problemas de decisão que têm algoritmo determinístico "
               "polinomial no comprimento da entrada. <b>NP</b> reúne aqueles cujas "
               "respostas sim têm certificados de tamanho polinomial verificáveis "
               "em tempo polinomial. P ⊆ NP. A igualdade P = NP permanece em aberto.")
        self.p("Decisão e redução", "sub")
        self.p("Dado ainda um alvo inteiro V, a versão de decisão pergunta se existe "
               "um subconjunto com peso total ≤ W e valor total ≥ V. Um vetor de n bits "
               "certifica as escolhas. Somar os pesos e valores em binário e testar os "
               "dois limites custa tempo polinomial no tamanho da instância.")
        self.p("Reduzimos Subset Sum, que é NP-completo, à decisão da Mochila 0/1. "
               "Para inteiros não negativos a₁, …, aₙ e alvo B, construímos um item "
               "com peso e valor aᵢ para cada número e usamos W = V = B. A mesma "
               "soma deve ser ≤ B pelo peso e ≥ B pelo valor. Uma escolha viável "
               "atinge exatamente B, e qualquer subconjunto que soma B satisfaz "
               "ambos os limites. A transformação copia dados em tempo polinomial. "
               "Isso prova NP-dificuldade e, junto à verificação, NP-completude. "
               "A decisão pertence a P se e somente se P = NP. A otimização é NP-difícil, "
               "pois seu valor ótimo decide se o alvo foi atingido. [2]")
        self.p("Pseudopolinomialidade", "sub")
        self.p("Se W = 2ᵇ − 1, sua descrição binária tem b bits e a tabela usa 2ᵇ colunas. "
               "O custo O(nW) para dimensões positivas é polinomial em n e no "
               "valor numérico de W. Com codificação binária, o número de colunas "
               "pode crescer exponencialmente mesmo com n fixo. [1]")
        self.p("Mochila fracionária", "sub")
        self.p("Ao permitir xᵢ ∈ [0, 1], podemos incluir itens de peso zero com "
               "valor positivo e ordenar os demais por vᵢ/wᵢ decrescente. "
               "Se uma solução usa peso de um item de menor densidade enquanto "
               "ainda pode usar peso de outro de maior densidade, trocar a mesma "
               "quantidade de peso melhora ou preserva o valor. Repetir essa troca "
               "leva à escolha gulosa, com O(n log n) comparações na ordenação. Com entradas "
               "binárias, comparar densidades por produtos cruzados e verificar se o ótimo "
               "fracionário atinge um alvo têm custo polinomial. A decisão fracionária está em P. "
               "As frações tornam viáveis as trocas de peso. No exemplo da seção 1, "
               "a escolha 0/1 pela razão soma 160, enquanto o ótimo inteiro é 220. "
               "A estratégia fracionária acrescenta 20/30 do terceiro item e soma 240. [3]")
        self.p("Conclusão", "sub")
        self.p("A enumeração é uma referência exata para instâncias pequenas. A "
               "tabulação ampliou a faixa prática de n quando a capacidade era "
               "moderada. O custo de sua tabela cresce com W, como mostraram as "
               "medições com 12 itens. Esses dois parâmetros orientam a escolha do algoritmo.")

    def creditos(self, equipe):
        self.pagina("Contribuições e referências")
        self.p("Contribuições dos integrantes", "sub")
        self.tabela([["Integrante", "Contribuição efetiva"]] +
                    [[e["nome"], e["contribuicao"]] for e in equipe["integrantes"]],
                    [170, 303], "Tabela 6. Dados acadêmicos editáveis em relatorio/equipe.json.")
        self.p("Declaração de uso de inteligência artificial", "sub")
        self.p("O Codex, da OpenAI, foi utilizado para implementar os algoritmos e os scripts, "
               "preparar testes, executar e revisar a coleta, analisar os dados e redigir "
               "a documentação, o relatório e a apresentação. Os valores experimentais "
               "vieram das execuções registradas nos CSV do projeto.")
        self.p("Referências bibliográficas e técnicas", "sub")
        for i, (citacao, *urls) in enumerate(REFERENCIAS, start=1):
            links = " · ".join(f'<link href="{url}" color="{VERDE}">'
                               f'{"Acessar fonte" if len(urls) == 1 else f"Documento {j}"}</link>'
                               for j, url in enumerate(urls, start=1))
            self.p(f"[{i}] {escape(citacao)} {links}.")
        self.p("Disponibilidade", "sub")
        self.p("O repositório inclui os dados de entrada, o manifesto de geração, "
               "os CSV brutos e agregados, os gráficos em 240 dpi e os scripts de "
               "reprodução. O README descreve como repetir a coleta no Windows.")

    def apendice(self):
        self.pagina("Apêndice  Comparações por algoritmo e linguagem")
        for nomes, legenda in (
            (("01_tempo_forca_bruta", "02_tempo_programacao_dinamica"),
             "Figura 9. Comparações entre Python e C dentro de cada algoritmo."),
            (("03_tempo_python", "04_tempo_c"),
             "Figura 10. Comparações entre algoritmos dentro de cada linguagem."),
        ):
            self.partes.append(Table([[self.imagem(n, 231) for n in nomes]],
                                     colWidths=[244, 244], hAlign="LEFT"))
            self.p(legenda, "legenda")
        self.p("As figuras usam os mesmos seis tamanhos da série principal, com "
               "20 execuções por ponto. A escala vertical é logarítmica e as barras "
               "mostram um desvio-padrão amostral. As versões individuais em PNG "
               "estão em resultados/graficos.")


def gerar(pasta, destino, arquivo_equipe):
    preparar_fontes()
    equipe = json.loads(arquivo_equipe.read_text(encoding="utf-8"))
    if len(equipe["integrantes"]) != 4:
        raise ValueError("A ficha deve conter os quatro integrantes.")
    relatorio = Relatorio(Dados(pasta))
    relatorio.capa(equipe)
    relatorio.algoritmos()
    relatorio.complexidade()
    relatorio.metodologia()
    relatorio.tempos()
    relatorio.crescimento()
    relatorio.capacidade()
    relatorio.memoria()
    relatorio.teoria()
    relatorio.creditos(equipe)
    relatorio.apendice()
    destino.parent.mkdir(exist_ok=True, parents=True)
    documento = SimpleDocTemplate(
        str(destino), pagesize=A4, leftMargin=52, rightMargin=52, topMargin=53,
        bottomMargin=61, title="Mochila 0/1 em Python e C", subject="Teoria da Computação",
    )
    documento.build(relatorio.partes, onFirstPage=moldura, onLaterPages=moldura)
    print(f"PDF gerado: {destino}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=RAIZ / "resultados")
    parser.add_argument("--pdf", type=Path, default=RAIZ / "relatorio" / "relatorio_mochila_01.pdf")
    parser.add_argument("--equipe", type=Path, default=RAIZ / "relatorio" / "equipe.json")
    args = parser.parse_args()
    gerar(args.saida, args.pdf, args.equipe)
