FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

# uv binary, pinned to an exact version + digest
COPY --from=ghcr.io/astral-sh/uv:0.12.9@sha256:8b940d3a9d65bed080436972241af2e21c84b5e8c9193f7014ed71479ee795ff /uv /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# install exactly what uv.lock pins; fail if uv.lock is out of date with pyproject.toml
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache

# relevant app files (certs and models are mounted at runtime)
COPY src/ ./src/
COPY scripts/run.py ./scripts/run.py

# non-root user
RUN mkdir -p /app/photos \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app/photos
USER app

# python as PID 1 (the venv is on PATH), so SIGTERM from `docker stop` reaches
# uvicorn directly and triggers its graceful shutdown
CMD ["python", "-m", "scripts.run"]
