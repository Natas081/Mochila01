param(
    [string]$Saida = 'resultados',
    [string]$Gcc = 'gcc',
    [string]$Python = 'python',
    [string]$Pdf
)

$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & $Python -m experimentos.executar_experimentos --gcc $Gcc --saida $Saida
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python -m experimentos.gerar_graficos --saida $Saida
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (!$Pdf) {
        $Pdf = Join-Path $Saida 'relatorio_mochila_01.pdf'
    }
    & $Python -m relatorio.gerar_relatorio --saida $Saida --pdf $Pdf
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
