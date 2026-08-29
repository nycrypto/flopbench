[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "test-unit",
        "test-contract",
        "test-integration",
        "test-security",
        "test-web",
        "test-all",
        "lint",
        "typecheck",
        "build"
    )]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$LocalPython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
$PythonCommand = if (Test-Path -LiteralPath $LocalPython) { $LocalPython } else { "python" }
Push-Location -LiteralPath $RepositoryRoot

try {
    switch ($Task) {
        "test-unit" { & $PythonCommand -m nox -s unit }
        "test-contract" { & $PythonCommand -m nox -s contract }
        "test-integration" { Write-Output "Integration tests begin in a later stage." }
        "test-security" { Write-Output "Security suites begin with the relevant implementation stages." }
        "test-web" { pnpm --filter "@flopbench/web" test }
        "test-all" {
            & $PythonCommand -m nox -s unit contract
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            pnpm --filter "@flopbench/web" test
        }
        "lint" {
            & $PythonCommand -m nox -s lint
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            pnpm --filter "@flopbench/web" lint
        }
        "typecheck" {
            & $PythonCommand -m nox -s typecheck
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            pnpm --filter "@flopbench/web" typecheck
        }
        "build" {
            & $PythonCommand -m nox -s build
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            pnpm --filter "@flopbench/web" build
        }
    }

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
