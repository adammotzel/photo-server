# App Container

The app runs in a Docker container, built from the `Dockerfile` and orchestrated with `compose.yaml`. Postgres is **not** containerized; it stays on the host, configured ahead of time (see [POSTGRES.md](../setup/POSTGRES.md)). Only the FastAPI app is containerized. This keeps the API/service layer decoupled from the database layer.

## Image

### Base + dependency install

The image starts from `python:3.12-slim` and pulls the `uv` binary straight from its official image:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
```

That avoids an install step and keeps `uv` at whatever the current release is.

Dependencies are installed *before* the app code is copied in:

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache
```
The flags:

- `--frozen`: install exactly what `uv.lock` pins, and fail rather than silently re-resolving. The lock file is the source of truth.
- `--no-dev`: skip the dev dependency group. Test and lint tooling has no reason to be in a runtime image.
- `--no-install-project`: install only the dependencies, not the project itself. The project code isn't in the image yet at this point, and installing it here would defeat the caching split.
- `--no-cache`: don't leave `uv`'s download cache in the image layer.

### Environment

```dockerfile
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
```

- `UV_COMPILE_BYTECODE=1`: pre-compile `.pyc` files at build time so startup doesn't pay for it.
- `UV_LINK_MODE=copy`: copy files instead of hardlinking, which avoids warnings when the cache and target sit on different layers/filesystems.
- `PYTHONPATH=/app`: makes `src.app` and `scripts.run` importable, matching how the app is run outside the container.
- `PYTHONUNBUFFERED=1`: without this, Python buffers stdout and logs appear in chunks (or not at all until exit) under `docker compose logs`.
- `PATH` with the venv first: `python` resolves to the venv interpreter without needing activation.

### What gets copied

```dockerfile
COPY src/ ./src/
COPY scripts/run.py ./scripts/run.py
COPY models/ ./models/
```

Only what the app needs at runtime.

`models/` is baked into the image because the classifier weights are static. They're part of what the image *is*, and change only when the model is retrained.

`certs/` is deliberately **not** copied in. It's mounted at runtime instead (see below), so the self-signed private key never lands in an image layer. Baking it in would also mean a full rebuild every time the cert is rotated, since it expires on a 365-day clock.

### Non-root user

```dockerfile
RUN mkdir -p /app/photos \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app/photos
USER app
```

The app runs as an unprivileged user rather than root. `/app/photos` is created and chowned before the `USER` switch, so the app can write uploads to it. A fixed, high UID (`10001`) keeps ownership predictable and avoids colliding with host system users.

### Entrypoint

```dockerfile
CMD ["uv", "run", "--no-sync", "python", "-m", "scripts.run"]
```

`--no-sync` tells `uv` not to re-check or re-resolve the environment at startup. The image was built with the exact locked dependencies, so syncing at runtime would be wasted work (and would fail in a read-only or offline context).

`scripts/run.py` calls `load_dotenv()` only if `NETWORK_NAME` is unset. In the container the environment is already populated by compose, so the `.env` load is skipped; outside the container it still works.

## Compose

`compose.yaml` handles everything that varies at runtime.

### `.env` does two different jobs

The same `.env` file is read twice, by two different mechanisms:

1. **Compose interpolation**: Compose automatically reads `.env` from the project directory to resolve `${...}` expressions *in the compose file itself*. That's what makes `"${SERVER_PORT:-8000}:${SERVER_PORT:-8000}"` work, with `8000` as the fallback if the variable is missing.
2. **`env_file: .env`**: Passes the variables into the container's environment at runtime, which is where the app actually reads them.

### Overrides

```yaml
environment:
  DB_HOST: host.docker.internal
```

**`DB_HOST`**: in `.env` this is `localhost`, which inside a container refers to the *container itself*, not the host machine, so Postgres would be unreachable. `host.docker.internal` resolves to the host. `extra_hosts: ["host.docker.internal:host-gateway"]` is included because Docker Desktop provides that name automatically but Linux hosts don't.

### Mounts

```yaml
volumes:
  - ./photos:/app/photos
  - ./certs:/app/certs:ro
```

**`photos`**: Uploads go to a bind mount. Without this, every `docker compose down` (or any image rebuild) would silently destroy every uploaded photo, while the `photos` rows in Postgres survived on the host, leaving the DB referencing files that no longer exist. Gallery thumbnails are written to a `thumbnails/` subfolder of this same directory (see [API](API.md)), so they persist on the same mount and need no volume of their own.

**`certs`**: The TLS key pair is mounted rather than copied into the image, so the private key stays on the host and out of every image layer. It's mounted `:ro` because the app only ever reads the certs. The practical payoff is cert rotation: regenerating the pair on the host and running `docker compose restart` picks up the new cert, with no rebuild.

## Commands

Run all of these from the project root.

### Build and run

```bash
docker compose up --build -d
```

Builds the image, tags it `photo-server:latest` (per `image:` in the compose file), and starts the container detached. Drop `-d` to run in the foreground.

After the first build, `--build` is only needed when something that goes *into* the image changes (`src/`, `scripts/run.py`, `models/`, `pyproject.toml`, `uv.lock`). Note that `certs/` is not on that list — it's mounted, so a new cert only needs a restart:

```bash
docker compose up -d
```

### Day-to-day

```bash
docker compose logs -f  # tail app logs
docker compose ps       # status and published ports
docker compose restart  # restart without rebuilding
docker compose stop     # stop, keep the container
docker compose down     # stop and remove the container
```

### Inspecting a running container

```bash
docker compose exec app sh  # shell inside the running container
docker compose exec app ls /app/photos | wc -l  # file count as the container sees it
docker compose exec app ls -l /app/certs  # confirm the cert mount landed
```

The photo count is the quickest mount sanity check: it should match `ls photos/ | wc -l` on the host. If the container's count is 0 (or just the files from the current session) while the host has more, the bind mount isn't pointing where it's supposed to.

### Prerequisites

- **Postgres must be running on the host** before starting the container. The app connects out to it via `host.docker.internal`.
- **`certs/` must exist at start time**, since it's mounted. Generate the pair first if missing (see [CONFIG.md](../setup/CONFIG.md)). If the directory is missing, Docker creates an empty one and the app fails at startup on the missing key file rather than serving without TLS. Rotating certs needs only `docker compose restart`, not a rebuild.
