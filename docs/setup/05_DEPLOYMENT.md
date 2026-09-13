# Deployment

The app runs in a Docker container, but Postgres stays on the host (see [01_POSTGRES.md](01_POSTGRES.md)).

## Before You Start

1. Install Docker Engine and the Compose plugin.
2. Start Postgres on the host (see [01_POSTGRES.md](01_POSTGRES.md)).
3. Create `.env` in the project root (see [02_CONFIG.md](02_CONFIG.md)).
4. Generate the TLS cert and key in `certs/` (see [02_CONFIG.md](02_CONFIG.md)).
5. Put the classifier files in `models/` (see [03_CLASSIFIER.md](03_CLASSIFIER.md)).

Make sure Postgres accepts connections from the Docker network, and that the host firewall permits inbound traffic to `SERVER_PORT`.

## Build and Run

From the project root:

```bash
bash scripts/build.sh
docker compose up -d
```

`scripts/build.sh` tags the image `photo-server:<version>-<sha>` from the `pyproject.toml` version and the short git SHA of `HEAD`, builds it with `docker compose build`, and writes `PHOTO_SERVER_TAG=<version>-<sha>` into `.env`. `compose.yaml` reads that variable to pick the image to run, so `docker compose up -d` runs the build you just made. There is no `latest` tag; to run an older build, set `PHOTO_SERVER_TAG` in `.env` by hand.

`-d` runs the container in the background. Compose:

- publishes `SERVER_PORT` to the host;
- mounts `./photos` at `/app/photos`, so uploaded photos persist on the host;
- mounts `./certs` and `./models` read-only, so the TLS key and classifier weights stay on the host and out of the image;
- restarts the container after a crash or host reboot, but not after a manual stop.

Open the app at `https://<host LAN IP>:<SERVER_PORT>`.

A rebuild is only needed when something in the image changes (`src/`, `scripts/run.py`, `pyproject.toml`, `uv.lock`, `Dockerfile`). A new cert or a retrained model just needs `docker compose restart`.

## Manage the App

```bash
docker compose ps           # status and published ports
docker compose logs -f app  # tail logs
docker compose restart      # restart without rebuilding
docker compose down         # stop and remove the container
```

Photos in `./photos` stay on the host across `docker compose down`.

### Stopping gracefully

Photo descriptions are written in the background after an upload returns, so a stop has to wait for them. On `docker compose down`, `restart`, or `stop`, uvicorn stops accepting requests and waits up to 90 seconds (`timeout_graceful_shutdown` in `scripts/run.py`) for in-flight descriptions before closing the database pool. Compose gives it 100 seconds (`stop_grace_period` in `compose.yaml`) before killing the container; keep that value above uvicorn's. Each OpenAI call is capped at 30 seconds with one retry (`OPENAI_TIMEOUT_S` / `OPENAI_MAX_RETRIES` in `src/config.py`), so a stop takes about a minute at worst.

A crash, OOM kill, or power loss can't wait: a description in flight then is lost, and that photo stays without one.
