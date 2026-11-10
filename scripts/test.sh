#!/usr/bin/env sh
# Run every check: Python tests, TypeScript type-check, front-end unit tests, production build.
set -e
cd "$(dirname "$0")/.."
echo "=== Python tests ===";            python -m pytest -q
cd web
echo "=== TypeScript type-check ===";   npm run typecheck
echo "=== Front-end unit tests ===";    npm test
echo "=== Production build ===";        npm run build
echo "All checks passed."
