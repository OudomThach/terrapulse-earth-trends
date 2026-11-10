# Development mode: API with auto-reload (port 8000) + Vite dev server with hot reload (port 5173).
# Open http://localhost:5173
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; python -m server --port 8000 --reload"

Set-Location "$root/web"
if (-not (Test-Path "node_modules")) { npm ci --no-audit --no-fund }
Write-Host "Web: http://localhost:5173  (proxying /api to :8000)" -ForegroundColor Green
npm run dev
