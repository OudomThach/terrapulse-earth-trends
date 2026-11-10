# Run TerraPulse locally (API + web app) on http://localhost:8000
#   .\scripts\start.ps1            build the web app if needed, then start
#   .\scripts\start.ps1 -Rebuild   force a fresh web build first
param([switch]$Rebuild, [int]$Port = 8000)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($Rebuild -or -not (Test-Path "web/dist/index.html")) {
    Write-Host "Building the web app..." -ForegroundColor Cyan
    Push-Location web
    if (-not (Test-Path "node_modules")) { npm ci --no-audit --no-fund }
    npm run build
    Pop-Location
}

Write-Host "TerraPulse: http://localhost:$Port   (API docs: http://localhost:$Port/docs)" -ForegroundColor Green
python -m server --port $Port
