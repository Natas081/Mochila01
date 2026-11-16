"""Executa a coleta pareada, o piloto e a coleta de memória com retomada."""

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys

from experimentos.comum import FLAGS, PROGRAMAS, RAIZ, compilar, executar, substituir_arquivo
from experimentos.gerar_entradas import PASTA_DADOS, PILOTO_MAX, SEMENTE, TAMANHOS, gerar
from experimentos.medir_memoria import CAMPOS, REPETICOES as REPETICOES_MEM, medir
from testes.testar_corretude import validar

REPETICOES_TEMPO = 20
LIMITE_S = 60
TIMEOUT_S = 62
TIMEOUT_MEM_S = 180
CHAVES = ("id", "serie", "n", "W", "sha256")
CAMPOS_BASE = (*CHAVES, "repeticao", "ordem", "linguagem", "algoritmo", "otimo")
CAMPOS_PILOTO = (*CHAVES, "linguagem", "status", "tempo_ns", "otimo", "otimo_pd")


@contextmanager
def travar_saida(pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    with (pasta / ".em_execucao").open("a+b") as trava:
        trava.seek(0)
        try:
            msvcrt.locking(trava.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as erro:
            raise RuntimeError(f"A pasta já está em uso por outra coleta: {pasta}") from erro
        try:
            yield
        finally:
            trava.seek(0)
            msvcrt.locking(trava.fileno(), msvcrt.LK_UNLCK, 1)


def ambiente(gcc):
    consulta = """
        $os = Get-CimInstance Win32_OperatingSystem
        $cpu = Get-CimInstance Win32_Processor
        $pc = Get-CimInstance Win32_ComputerSystem
        [ordered]@{
            sistema = $os.Caption
            versao_sistema = $os.Version
            cpu = ($cpu.Name -join ', ')
            ram_bytes = [long] $pc.TotalPhysicalMemory
        } | ConvertTo-Json -Compress
    """
    hardware = json.loads(subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-Command", consulta], text=True,
    ))
    fontes = [p for pasta in ("c", "python", "experimentos", "testes")
              for p in (RAIZ / pasta).iterdir()
              if p.suffix in (".c", ".h", ".py") and p.name != "gerar_graficos.py"]
    sha = hashlib.sha256()
    for fonte in sorted(fontes):
        sha.update(fonte.relative_to(RAIZ).as_posix().encode("ascii") + b"\0")
        sha.update(fonte.read_bytes())

    return {
        **hardware, "python": sys.version, "python_bits": 8 * struct.calcsize("P"),
        "arquitetura_host": platform.machine(),
        "gcc": subprocess.check_output([gcc, "--version"], text=True).splitlines()[0],
        "alvo_gcc": subprocess.check_output([gcc, "-dumpmachine"], text=True).strip(),
        "flags_c": [*FLAGS, "-lpsapi"],
        "fonte_sha256": sha.hexdigest(),
        "manifesto_sha256": hashlib.sha256((PASTA_DADOS / "manifesto.json").read_bytes()).hexdigest(),
        "semente": SEMENTE, "tamanhos": list(TAMANHOS),
        "repeticoes_tempo": REPETICOES_TEMPO, "repeticoes_memoria": REPETICOES_MEM,
        "limite_piloto_s": LIMITE_S, "timeout_pareado_s": TIMEOUT_S,
        "timeout_memoria_s": TIMEOUT_MEM_S,
    }


def registrar_ambiente(pasta, registro):
    destino = pasta / "ambiente.json"
    if destino.exists():
        anterior = json.loads(destino.read_text(encoding="utf-8"))
        anterior.pop("inicio_utc")
        if anterior != registro:
            mudancas = [campo for campo in registro if anterior.get(campo) != registro[campo]]
            raise RuntimeError(f"Coleta incompatível ({', '.join(mudancas)}). Use outra --saida.")
        return
    temporario = destino.with_suffix(".tmp")
    registro = {"inicio_utc": datetime.now(timezone.utc).isoformat(), **registro}
    temporario.write_text(json.dumps(registro, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    substituir_arquivo(temporario, destino)


def carregar_csv(caminho, campos):
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if tuple(leitor.fieldnames or ()) != campos:
            raise ValueError(f"Colunas inesperadas em {caminho}")
        return list(leitor)


def salvar_csv(caminho, campos, linhas):
    temporario = caminho.with_suffix(".csv.tmp")
    with temporario.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, campos)
        escritor.writeheader()
        escritor.writerows(linhas)
        arquivo.flush()
        os.fsync(arquivo.fileno())
    substituir_arquivo(temporario, caminho)


def conferir_otimo(resultados):
    valores = {r["otimo"] for r in resultados}
    if len(valores) != 1 or not all(type(r["otimo"]) is int and r["otimo"] >= 0
                                    for r in resultados):
        raise RuntimeError(f"Divergência de corretude: {resultados}")
    return valores.pop()


def coletar_pareado(instancias, caminho, modo):
    memoria = modo == "memoria"
    campos = (*CAMPOS_BASE, *CAMPOS) if memoria else (*CAMPOS_BASE, "tempo_ns")
    repeticoes = REPETICOES_MEM if memoria else REPETICOES_TEMPO
    linhas = carregar_csv(caminho, campos)
    existentes = {}
    for linha in linhas:
        chave = (linha["id"], int(linha["repeticao"]))
        existentes.setdefault(chave, []).append(linha)
    for instancia in instancias:
        ident = instancia["id"]
        entrada = (PASTA_DADOS / instancia["arquivo"]).read_bytes()
        for repeticao in range(1, repeticoes + 1):
            ordem = list(PROGRAMAS)
            random.Random(f"{SEMENTE}/{modo}/{ident}/{repeticao}").shuffle(ordem)
            anteriores = existentes.get((ident, repeticao))
            if anteriores:
                realizados = [(r["linguagem"], r["algoritmo"]) for r in anteriores]
                if realizados != ordem or len({r["otimo"] for r in anteriores}) != 1:
                    raise RuntimeError(f"Checkpoint inconsistente em {ident}, repetição {repeticao}")
                continue

            bloco = []
            for posicao, (linguagem, algoritmo) in enumerate(ordem, start=1):
                if memoria:
                    resultado = medir(linguagem, algoritmo, entrada, TIMEOUT_MEM_S)
                else:
                    resultado = executar(linguagem, algoritmo, entrada, timeout=TIMEOUT_S)
                    if type(resultado["tempo_ns"]) is not int or resultado["tempo_ns"] <= 0:
                        raise RuntimeError(f"Tempo inválido: {linguagem}/{algoritmo} {resultado}")
                bloco.append({
                    **{campo: instancia[campo] for campo in CHAVES}, "repeticao": repeticao,
                    "ordem": posicao, "linguagem": linguagem, "algoritmo": algoritmo,
                    **resultado,
                })
            otimo = conferir_otimo(bloco)
            if any(r["id"] == ident and int(r["otimo"]) != otimo for r in linhas):
                raise RuntimeError(f"O ótimo mudou entre repetições em {ident}.")
            linhas.extend(bloco)
            salvar_csv(caminho, campos, linhas)
        print(f"{modo}: {ident} ({repeticoes} repetições por programa)", flush=True)


def executar_piloto(instancias, caminho):
    por_n = {i["n"]: i for i in instancias if i["serie"] == "piloto"}
    linhas = carregar_csv(caminho, CAMPOS_PILOTO)
    existentes = {(r["linguagem"], int(r["n"])): r for r in linhas}
    for linguagem in ("Python", "C"):
        n = TAMANHOS[-1]
        viavel, inviavel = n - 1, PILOTO_MAX + 1
        while viavel + 1 < inviavel:
            linha = existentes.get((linguagem, n))
            if linha is None:
                instancia = por_n[n]
                entrada = (PASTA_DADOS / instancia["arquivo"]).read_bytes()
                oraculo = conferir_otimo([
                    executar(ling, "programacao_dinamica", entrada, "--valor", timeout=10)
                    for ling in ("Python", "C")
                ])
                try:
                    resultado = executar(linguagem, "forca_bruta", entrada, timeout=TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    resultado = {"tempo_ns": "", "otimo": ""}
                    status = "timeout"
                else:
                    conferir_otimo([resultado, {"otimo": oraculo}])
                    status = "viavel" if resultado["tempo_ns"] <= LIMITE_S * 1e9 else "acima_limite"
                linha = {
                    **{campo: instancia[campo] for campo in CHAVES}, "linguagem": linguagem,
                    "status": status, "otimo_pd": oraculo, **resultado,
                }
                linhas.append(linha)
                salvar_csv(caminho, CAMPOS_PILOTO, linhas)
                print(f"piloto: {linguagem}, n={n}, {status}, {resultado['tempo_ns']} ns",
                      flush=True)

            if linha["status"] == "viavel":
                viavel = n
                if viavel == PILOTO_MAX:
                    raise RuntimeError("Teto de segurança do piloto alcançado sem fixar o limite.")
            else:
                inviavel = n
            if viavel + 1 == inviavel:
                break
            if inviavel <= PILOTO_MAX:
                n = (viavel + inviavel) // 2
            else:
                proximo = n + 1
                # Projeta por n*2^n para evitar tentativas lentas muito abaixo do limiar.
                for candidato in range(n + 2, min(n + 4, PILOTO_MAX) + 1):
                    estimativa = int(linha["tempo_ns"]) / 1e9 * candidato / n * 2**(candidato - n)
                    if estimativa <= LIMITE_S * 0.8:
                        proximo = candidato
                n = proximo
        if viavel < TAMANHOS[-1]:
            raise RuntimeError("O ponto inicial do piloto excedeu o limite neste computador.")
        print(f"limite observado: {linguagem}, n={viavel}; n={inviavel} excedeu o limite.",
              flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcc", default="gcc")
    parser.add_argument("--saida", type=Path, default=RAIZ / "resultados")
    parser.add_argument("--etapa", choices=("tudo", "tempo", "piloto", "memoria"), default="tudo")
    args = parser.parse_args()
    with travar_saida(args.saida):
        compilar(args.gcc)
        validar()
        manifesto = gerar()
        tabelas = args.saida / "tabelas"
        tabelas.mkdir(exist_ok=True)
        registrar_ambiente(args.saida, ambiente(args.gcc))
        instancias = [i for i in manifesto if i["serie"] != "piloto"]
        if args.etapa in ("tudo", "tempo"):
            coletar_pareado(instancias, tabelas / "tempo_bruto.csv", "tempo")
        if args.etapa in ("tudo", "piloto"):
            executar_piloto(manifesto, tabelas / "piloto.csv")
        if args.etapa in ("tudo", "memoria"):
            coletar_pareado(instancias, tabelas / "memoria_bruta.csv", "memoria")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Execução interrompida. Rode o mesmo comando para retomar.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as erro:
        raise SystemExit(f"Coleta interrompida: {erro}") from erro
