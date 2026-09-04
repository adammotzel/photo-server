# App Container

The app runs in a Docker container, built from the `Dockerfile` and orchestrated with `compose.yaml`. The Postgres database is **not** containerized; it stays on the host (see [01_POSTGRES.md](../setup/01_POSTGRES.md)). Only the FastAPI app is containerized. This keeps the API/service layer decoupled from the database layer.

## Image

### Base + dependency install

The image starts from `python:3.12-slim`, pinned by digest, and pulls the `uv` binary straight from its official image at a pinned version + digest:

```dockerfile
FROM python:3.12-slim@sha256:<digest>

COPY --from=ghcr.io/astral-sh/uv:0.12.9@sha256:<digest> /uv /bin/
```

Pinning both by digest means a rebuild uses byte-for-byte the same base layers and the same `uv`, rather than whatever the `python:3.12-slim` / `uv:latest` tags happen to point at that day. To bump either, resolve the new digest with `docker buildx imagetools inspect <ref>` and update the `Dockerfile` line (pin the multi-arch *index* digest, not a per-platform manifest).

Dependencies are installed *before* the app code is copied in:

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache
```
The flags:

- `--locked`: install exactly what `uv.lock` pins, and additionally fail the build if `uv.lock` is out of date with `pyproject.toml`. The lock file is the source of truth, and this proves it is current. (`--frozen` would install from the lock without that consistency check.)
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
```

Only what the app needs at runtime.

`certs/` and `models/` are deliberately **not** copied in. Both are mounted at runtime instead (see below). For `certs/`, this keeps the self-signed private key out of every image layer, and means cert rotation needs no rebuild since the cert expires on a 365-day clock. For `models/`, this keeps the classifier weights out of the image entirely; swapping in a retrained model is a matter of updating the host directory and restarting, not rebuilding.

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

## Compose

`compose.yaml` handles everything that varies at runtime.

### `.env` does two different jobs

The same `.env` file is read twice, by two different mechanisms:

1. **Compose interpolation**: Compose automatically reads `.env` from the project directory to resolve `${...}` expressions *in the compose file itself*. That's what makes `"${SERVER_PORT:-8000}:${SERVER_PORT:-8000}"` work, with `8000` as the fallback if the variable is missing. It's also how `image: photo-server:${PHOTO_SERVER_TAG:?...}` resolves; `scripts/build.sh` writes `PHOTO_SERVER_TAG` here after each build, and the `:?` form makes Compose refuse to start if it's unset (i.e. nothing has been built yet).
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
  - ./models:/app/models:ro
```

**`photos`**: Uploads go to a bind mount. Without this, every `docker compose down` (or any image rebuild) would silently destroy every uploaded photo, while the `photos` rows in Postgres survived on the host, leaving the DB referencing files that no longer exist. Gallery thumbnails are written to a `thumbnails/` subfolder of this same directory (see [API](API.md)), so they persist on the same mount and need no volume of their own.

**`certs`**: The TLS key pair is mounted rather than copied into the image, so the private key stays on the host and out of every image layer. It's mounted `:ro` because the app only ever reads the certs. The practical payoff is cert rotation: regenerating the pair on the host and running `docker compose restart` picks up the new cert, with no rebuild.

**`models`**: The classifier weights are mounted rather than copied into the image for the same reason — they're mounted `:ro` because the app only reads them at startup. The practical payoff is size: the weight files are large, and keeping them off the image means smaller images and faster builds/pulls. Deploying a retrained model is dropping the new files in `models/` on the host and running `docker compose restart`, no rebuild.

## Commands

Run all of these from the project root.

### Build and run

```bash
bash scripts/build.sh
docker compose up -d
```

`scripts/build.sh` is the only supported way to build the image. It:

- refuses to run unless you are on `main` with a clean working tree, so every image maps back to exactly one commit;
- reads the version from `pyproject.toml` (`[project].version`) and the short SHA from `git rev-parse --short HEAD`, giving one tag `photo-server:<version>-<sha>`. There is no `latest`;
- runs `docker compose build` with that tag passed as `PHOTO_SERVER_TAG` — `compose.yaml`'s `build:` section is what actually describes the build, so there's one definition of context and args;
- on success, writes `PHOTO_SERVER_TAG=<version>-<sha>` into `.env`.

`docker compose up -d` then starts the container from `photo-server:${PHOTO_SERVER_TAG}` — the build you just made. Drop `-d` to run in the foreground. To run an older build instead, set `PHOTO_SERVER_TAG` in `.env` to that tag by hand and `docker compose up -d`.

`compose.yaml` keeps its `build:` section, so `docker compose build` / `up --build` still work, but they skip the `main`-only and clean-tree checks and reuse whatever `PHOTO_SERVER_TAG` is already in `.env` — so a build from a dirty or non-`main` tree would be mislabelled with the previous commit's tag. Use `scripts/build.sh`.

A rebuild is only needed when something that goes *into* the image changes (`src/`, `scripts/run.py`, `pyproject.toml`, `uv.lock`, or the `Dockerfile`). `certs/` and `models/` are not on that list; both are mounted, so a new cert or a retrained model only needs `docker compose restart`.

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
- **`certs/` must exist at start time**, since it's mounted. Generate the pair first if missing (see [02_CONFIG.md](../setup/02_CONFIG.md)). If the directory is missing, Docker creates an empty one and the app fails at startup on the missing key file rather than serving without TLS. Rotating certs needs only `docker compose restart`, not a rebuild.
- **`models/` must contain the classifier weights at startup**, since it's mounted too. See [03_CLASSIFIER.md](../setup/03_CLASSIFIER.md) to produce them. If missing, the app fails at startup trying to load the model.
