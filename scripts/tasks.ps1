[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "test-unit",
        "test-contract",
        "test-integration",
        "test-security",
        "test-web",
        "test-e2e",
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
        "test-security" { & $PythonCommand -m nox -s security }
        "test-web" { pnpm --filter "@flopbench/web" test }
        "test-e2e" { pnpm --filter "@flopbench/web" e2e }
        "test-all" {
            & $PythonCommand -m nox -s unit contract security
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            pnpm --filter "@flopbench/web" test
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            pnpm --filter "@flopbench/web" e2e
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
