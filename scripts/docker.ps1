# Docker helper.
#   .\scripts\docker.ps1 up      build and start on http://localhost:8088
#   .\scripts\docker.ps1 test    run the Python tests inside a container
#   .\scripts\docker.ps1 down    stop (keeps saved data)
#   .\scripts\docker.ps1 reset   stop and delete saved data
#   .\scripts\docker.ps1 logs    follow the logs
param([Parameter(Position = 0)][ValidateSet("up", "test", "down", "reset", "logs")][string]$Action = "up")

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

switch ($Action) {
    "up"    { docker compose up --build -d; Write-Host "TerraPulse: http://localhost:8088" -ForegroundColor Green; docker compose ps }
    "test"  { docker compose --profile test run --rm --build tests }
    "down"  { docker compose down }
    "reset" { docker compose down -v }
    "logs"  { docker compose logs -f terrapulse }
}
