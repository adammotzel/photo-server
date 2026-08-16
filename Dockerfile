FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# use lock file
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# relevant app files (certs are mounted at runtime)
COPY src/ ./src/
COPY scripts/run.py ./scripts/run.py
COPY models/ ./models/

# non-root user
RUN mkdir -p /app/photos \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app/photos
USER app

CMD ["uv", "run", "--no-sync", "python", "-m", "scripts.run"]
