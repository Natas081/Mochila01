# Mochila 0/1 em Python e C

Projeto de Teoria da Computação sobre o valor máximo que se pode obter selecionando itens indivisíveis sob uma restrição de capacidade. Quatro executáveis resolvem a mesma instância por enumeração de máscaras ou tabulação bidimensional. O estudo mede tempo, pico de memória residente do processo e memória auxiliar.

## Arquivos

| Pasta ou arquivo | Conteúdo |
| --- | --- |
| `python/`, `c/` | Solucionadores, leitura de dados e instrumentação |
| `testes/` | Casos conhecidos, aleatórios com oráculo, entradas inválidas e teste dos medidores |
| `experimentos/` | Compilação, geração de entradas, coleta, auditoria, estatísticas e gráficos |
| `dados/` | Instâncias em texto e manifesto com sementes e SHA-256 |
| `resultados/` | Ambiente registrado, tabelas CSV brutas e agregadas, gráficos PNG em 240 dpi |
| `relatorio/` | PDF, fonte Python e metadados acadêmicos editáveis |
| `apresentacao/` | Slides em PowerPoint e roteiro de fala com perguntas e respostas |
| `reproduzir.ps1` | Automação da coleta, auditoria, gráficos e relatório |

O PDF e os slides são entregues à parte. O código publicado inclui o gerador do relatório e a coleta necessária para reproduzi-lo.

## Instalação no Windows 11

Abra esta pasta no VS Code e use o terminal PowerShell. Use Python 3.13 para instalar as versões fixadas dos pacotes. A coleta entregue utilizou Python 3.13.2 e GCC para Windows. Deixe `gcc.exe` no PATH ou passe seu caminho por `--gcc` ou `-Gcc`. Os solucionadores, testes e coletores usam a biblioteca padrão do Python. Os pacotes abaixo são necessários para as tabelas, gráficos e PDF.

```powershell
python --version
gcc --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Compilação, entradas e testes

```powershell
.\.venv\Scripts\python.exe -m experimentos.comum
.\.venv\Scripts\python.exe -m testes.testar_corretude --sem-compilar
.\.venv\Scripts\python.exe -m experimentos.gerar_entradas
```

O módulo de compilação executa os comandos abaixo. A opção `-lpsapi` liga a API de memória do Windows.

```powershell
New-Item -ItemType Directory -Force build | Out-Null
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror c/forca_bruta.c c/protocolo.c -o build/forca_bruta.exe -lpsapi
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror c/programacao_dinamica.c c/protocolo.c -o build/programacao_dinamica.exe -lpsapi
```

Cada programa lê `n W` seguido por `n` pares `peso valor` na entrada padrão. Use dígitos decimais ASCII sem sinal e separados por espaço em branco. Cada token contém até 19 dígitos e representa um inteiro de 0 a 2⁶³ − 1. Cada uma das duas somas de entrada deve caber nesse intervalo. O limite de 62 itens da interface da força bruta permite usar máscaras equivalentes nas duas linguagens. Limites de endereçamento, memória disponível e tempo praticável geralmente são atingidos bem antes disso. A linha de comandos devolve um objeto JSON por execução. Entradas inválidas produzem erro na saída de diagnóstico e código 2.

```powershell
Get-Content dados/principal_n04.txt | .\.venv\Scripts\python.exe python/forca_bruta.py
Get-Content dados/principal_n04.txt | .\.venv\Scripts\python.exe python/programacao_dinamica.py
Get-Content dados/principal_n04.txt | .\build\forca_bruta.exe
Get-Content dados/principal_n04.txt | .\build\programacao_dinamica.exe
```

A saída padrão contém `otimo` e `tempo_ns`. Use `--valor` para obter somente o ótimo. As opções `--mem-processo` e `--mem-aux` executam o solucionador sem cronometrar.

## Reprodução completa

Use um destino separado para preservar a coleta entregue. Feche cargas intensivas durante as medições. O piloto e o rastreamento de memória da força bruta podem levar vários minutos.

```powershell
.\reproduzir.ps1 -Python .\.venv\Scripts\python.exe -Saida build/reproducao
```

Se a política de execução do PowerShell bloquear scripts, use os três módulos diretamente.

```powershell
.\.venv\Scripts\python.exe -m experimentos.executar_experimentos --saida build/reproducao
.\.venv\Scripts\python.exe -m experimentos.gerar_graficos --saida build/reproducao
.\.venv\Scripts\python.exe -m relatorio.gerar_relatorio --saida build/reproducao --pdf build/reproducao/relatorio_mochila_01.pdf
```

O coletor recompila C e roda os testes antes de coletar. Cada bloco de quatro programas só entra no CSV quando todos retornam o mesmo ótimo. O piloto salva cada tentativa. Após Ctrl+C, execute o mesmo comando com o mesmo destino para continuar. A coleta valida ambiente, compilador, configuração e hashes antes de reutilizar os resultados. Para repetir medições do zero ou mudar de ambiente, aponte para uma pasta nova. A opção `--etapa tempo`, `--etapa piloto` ou `--etapa memoria` permite rodar uma fase por vez. A auditoria dos gráficos exige as três fases completas.

Para atualizar o relatório oficial, preencha os nomes e as contribuições efetivamente realizadas em `relatorio/equipe.json`. O campo de instituição é opcional. Em seguida, gere o PDF com o comando abaixo.

```powershell
.\.venv\Scripts\python.exe -m relatorio.gerar_relatorio
```

Preencha a identificação no primeiro slide antes de apresentar. O relatório usa os CSV resumidos e PNG já gerados. Os slides da entrega usam a coleta documentada em `resultados/`.

## Desenho experimental

- **Série principal.** Os seis tamanhos `n = 4, 6, 8, 11, 15, 20` vêm de `round(4 × 1,38ᵏ)`, para `k = 0, …, 5`. A razão geométrica é fixa antes do arredondamento para um número inteiro de itens. A escolha mantém a série repetida dentro de um intervalo viável para a enumeração e reserva os tamanhos próximos de 60 s para o piloto. A capacidade é `W = 20n`. Cada tamanho tem uma instância com pesos em [1, 50] e valores em [1, 100], gerada com `20261116 + n`.
- **Variação de W e dos pesos.** Com 12 itens e os mesmos pares, usamos `W = 0, 240, 2400, 24000`. No controle de pesos mantemos `n = 12`, `W = 240` e os mesmos valores, substituindo os pesos por 0 ou 241. Os quatro programas recebem os mesmos bytes em todas as comparações de tempo e memória.
- **Tempo.** Para cada instância são 20 blocos com ordem dos quatro programas embaralhada por semente fixa, um processo por medição, executado em série. A leitura, validação da entrada, inicialização do processo, geração e impressão ocorrem fora do intervalo cronometrado. O tempo inclui alocar e liberar a tabela no solucionador. Os relógios são `perf_counter_ns` no Python e `QueryPerformanceCounter` no C. O valor ótimo sai em JSON e é usado em todas as verificações.
- **Piloto.** Começa no maior tamanho da série principal. Projeta o próximo passo por `n × 2ⁿ`, sobe no máximo quatro itens por tentativa e, se necessário, refina o intervalo por busca binária até observar tamanhos adjacentes. Considera viável um tempo interno de até 60 s. Um watchdog encerra o subprocesso em 62 s de parede, com cerca de 2 s de margem para inicialização, entrada e saída. Um timeout é uma observação censurada, registrada com tempo em branco. Os dois programas de tabulação verificam cada instância do piloto e conferem o ótimo da força bruta quando ela conclui.
- **Memória.** Para cada instância e programa, três pares de subprocessos separam a medição do working set da medição auxiliar. O Windows mede a mesma grandeza para Python e C com `GetProcessMemoryInfo`, incluindo interpretador ou runtime, entrada, alocador, módulos e páginas residentes compartilhadas. Registra-se o working set atual e seu pico antes da chamada, além do pico histórico após a chamada. O delta entre picos tem interpretação de incremento do pico do processo.
- **Métricas auxiliares.** Python usa `tracemalloc` iniciado após a leitura, medindo o pico dos blocos rastreados na região da chamada, inclusive temporários. C contabiliza o payload do heap auxiliar solicitado. São zero bytes para a força bruta e `8(n+1)(W+1)` para a tabela. A pilha, o alocador e a entrada estão fora dessa contagem em C. A comparação direta entre linguagens usa o working set. As métricas auxiliares servem para avaliar a tendência dentro de cada implementação.

## Leitura dos resultados

| Arquivo | Unidades e conteúdo |
| --- | --- |
| `tempo_bruto.csv` | Ns e ótimo para cada execução, com número e ordem do bloco |
| `memoria_bruta.csv` | Bytes nos contadores de processo e na métrica auxiliar correspondente à linguagem, por par |
| `piloto.csv` | Tempos em ns quando concluídos, status, tamanhos e ótimo de referência |
| `tempo_resumo.csv` | Média, desvio-padrão amostral, mínimo e máximo em ns |
| `memoria_resumo.csv` | As mesmas estatísticas em bytes, por métrica |
| `crescimento_teorico.csv` | Contagens de trabalho e razão entre tempo médio e trabalho previsto |
| `ambiente.json` | Versões, opções de compilação, CPU, memória, SO e configuração |

Cada barra de erro representa ±1 desvio-padrão amostral. A série principal usa uma instância por tamanho e mede variação entre execuções dessa instância. Os perfis mostram o efeito de ramos e constantes com os mesmos limites assintóticos. Os tempos podem variar com a máquina, a arquitetura do binário, frequência, memória, aquecimento e escalonamento do sistema.
