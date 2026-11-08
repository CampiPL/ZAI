FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM python:3.12-slim-bookworm AS app
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 HOST=0.0.0.0 PORT=8000 DATABASE_PATH=/app/data/splot.sqlite3
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./backend/
COPY generator/ ./generator/
COPY scripts/ ./scripts/
COPY frontend/public/ ./frontend/public/
COPY --from=frontend /build/dist ./frontend/dist
RUN useradd --uid 10001 --create-home app && mkdir -p /app/data && chown -R app:app /app/data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"]
CMD ["/app/.venv/bin/python", "scripts/serve.py"]
