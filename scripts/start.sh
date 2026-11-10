#!/usr/bin/env sh
# Run TerraPulse locally (API + web app) on http://localhost:8000
set -e
cd "$(dirname "$0")/.."
if [ ! -f web/dist/index.html ]; then
  echo "Building the web app..."
  (cd web && { [ -d node_modules ] || npm ci --no-audit --no-fund; } && npm run build)
fi
echo "TerraPulse: http://localhost:${PORT:-8000}   (API docs: /docs)"
python -m server --port "${PORT:-8000}"
