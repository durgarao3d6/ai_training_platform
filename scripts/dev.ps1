# Windows wrapper around docker compose. Needs only Docker Desktop.
# Usage: ./scripts/dev.ps1 <up|down|test|lint|migrate|seed|content-validate|client|a11y|reset>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('up', 'down', 'test', 'test-integration', 'lint', 'migrate', 'seed', 'content-validate', 'client', 'a11y', 'reset')]
    [string]$Command
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

# --env-file: Compose interpolates from the project directory (infra/), not the repo root.
$base = @('--env-file', '.env', '-f', 'infra/compose.yml')
$dev = $base + @('-f', 'infra/compose.dev.yml')
$test = $base + @('-f', 'infra/compose.test.yml')

function Invoke-Compose {
    # Docker writes progress to stderr; do not let that count as a failure.
    $ErrorActionPreference = 'Continue'
    docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed ($LASTEXITCODE)" }
}

function Invoke-Tools([string]$Script) {
    Invoke-Compose @test --profile tools run --rm --no-deps tools sh -c $Script
}

switch ($Command) {
    'up' {
        if (-not (Test-Path .env)) { Copy-Item .env.example .env }
        Invoke-Compose @dev up --build -d --wait
    }
    'down' { Invoke-Compose @dev down }
    'test' { Invoke-Tools 'cd apps/api && python -m pytest -q' }
    'test-integration' {
        Invoke-Compose @test up -d --wait postgres s3
        Invoke-Tools 'cd apps/api && alembic upgrade head && RUN_INTEGRATION=1 python -m pytest -q'
    }
    'lint' {
        Invoke-Tools 'ruff check apps services && ruff format --check apps services && cd apps/api && mypy app tests'
        Invoke-Compose @dev run --rm --no-deps web sh -c 'npm run lint && npm run typecheck'
    }
    'migrate' { Invoke-Compose @dev run --rm api alembic upgrade head }
    'seed' { Invoke-Compose @dev run --rm api python -m app.seed.bootstrap }
    'content-validate' { Invoke-Tools 'cd apps/api && python -m app.content.cli validate /work/content' }
    'client' {
        Invoke-Tools 'cd apps/api && python -m app.api.export_openapi && openapi-typescript /work/packages/contracts/openapi.json -o /work/packages/contracts/client/schema.d.ts && cp /work/packages/contracts/client/schema.d.ts /work/apps/web/lib/api-schema.d.ts'
    }
    'a11y' {
        Invoke-Compose @test up --build -d --wait api web
        Invoke-Tools 'cd apps/api && alembic upgrade head && python -m app.seed.bootstrap && PYTHONPATH=. python tests/browser_fixture.py'
        Invoke-Compose @test --profile browser run --rm --no-deps browser
    }
    'reset' {
        Invoke-Compose @dev down -v
        if (-not (Test-Path .env)) { Copy-Item .env.example .env }
        Invoke-Compose @dev up --build -d --wait
    }
}
