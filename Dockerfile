# syntax=docker/dockerfile:1
# Multi-stage build: compile the TypeScript front end, then ship it next to the Python API.

# ---------------------------------------------------------------- 1. build the web app
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ---------------------------------------------------------------- 2. runtime image
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TERRAPULSE_DB=/app/storage/terrapulse.db \
    TERRAPULSE_WEB=/app/web/dist
WORKDIR /app

COPY requirements-server.txt .
RUN pip install -r requirements-server.txt

COPY terrapulse ./terrapulse
COPY server ./server
COPY data/cache ./data/cache
COPY --from=web /web/dist ./web/dist

# run as an unprivileged user; the database lives on a volume
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/storage \
    && chown -R app:app /app/storage /app/data
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=4s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"
CMD ["python", "-m", "server", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------- 3. test image (docker compose --profile test)
FROM runtime AS test
USER root
RUN pip install pytest==9.1.1 httpx==0.28.1 plotly==6.9.0
COPY tests ./tests
COPY pytest.ini ./
COPY examples ./examples
USER app
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
