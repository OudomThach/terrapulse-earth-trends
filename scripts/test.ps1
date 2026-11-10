# Run every check: Python tests, TypeScript type-check, front-end unit tests, production build.
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$failed = $false

function Step($name, $block) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $name" -ForegroundColor Red; $script:failed = $true }
}

Step "Python tests (statistics, forecasting, fire, API)" { python -m pytest -q }
Push-Location web
Step "TypeScript strict type-check"    { npm run typecheck }
Step "Front-end unit tests"            { npm test }
Step "Production build"                { npm run build }
Pop-Location

if ($failed) { Write-Host "`nSome checks failed." -ForegroundColor Red; exit 1 }
Write-Host "`nAll checks passed." -ForegroundColor Green
