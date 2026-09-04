# Deployment

This document tells you how to run the app in a Docker container.

Postgres does not run in a container. Postgres runs on the host machine (see [01_POSTGRES.md](01_POSTGRES.md)).

## Before You Start

Do these steps first:

1. Install Docker Engine and the Compose plugin.
2. Start Postgres on the host machine (see [01_POSTGRES.md](01_POSTGRES.md)).
3. Make the `.env` file in the project root (see [02_CONFIG.md](02_CONFIG.md)).
4. Make the TLS certificate and the key in the `certs/` directory (see [02_CONFIG.md](02_CONFIG.md)).
5. Store the classifier files in the `models/` directory (see [03_CLASSIFIER.md](03_CLASSIFIER.md)).

## The Image

The [Dockerfile](../../Dockerfile) makes the image in these steps:

1. It starts from the `python:3.12-slim` image, pinned by digest.
2. It copies the `uv` binary into the image, pinned to an exact version.
3. It installs the locked dependencies from `pyproject.toml` and `uv.lock` with `uv sync --locked`. It does not install the dev dependencies. The build fails if `uv.lock` is out of sync with `pyproject.toml`.
4. It copies `src/`, `scripts/run.py`, and `models/` into `/app`.
5. It makes the `/app/photos` directory and the non-root user `app`.
6. It runs the app with the command `uv run --no-sync python -m scripts.run`.

The certificates and the photos are not in the image. Docker mounts them at run time.

The [.dockerignore](../../.dockerignore) file keeps the tests, the docs, the notebooks, and the local secrets out of the build context.

## Environment Values

The container reads the `.env` file; [compose.yaml](../../compose.yaml) sets `DB_HOST` to `host.docker.internal`. The container uses this name to find Postgres on the host.

Make sure that Postgres accepts connections from the Docker network. Also make sure that the host firewall permits the port in `SERVER_PORT`.

## Build and Start the App

Build the image, then start the container:

```bash
bash scripts/build.sh
docker compose up -d
```

`scripts/build.sh` reads the version from `pyproject.toml` and the short git SHA of `HEAD` to form the tag `photo-server:<version>-<sha>`, then runs `docker compose build` with it. It refuses to run unless you are on a clean `main` checkout, so every image maps back to one commit.

On success it writes `PHOTO_SERVER_TAG=<version>-<sha>` into `.env` (creating the line or updating it in place). `compose.yaml` reads that variable to decide which image to run, so `docker compose up -d` always runs the image you just built. There is no `latest` tag. To run an older build, set `PHOTO_SERVER_TAG` in `.env` to that tag by hand.

The `-d` option starts the container in the background.

Compose does these things:

- It publishes the port in `SERVER_PORT` to the host.
- It mounts the host directory `./photos` on `/app/photos`. The uploaded photos stay on the host.
- It mounts the host directory `./certs` on `/app/certs` in read-only mode.
- It starts the container again after a failure or after a restart of the host. It does not start the container again after a manual stop.

Open the app at `https://<host LAN IP address>:<SERVER_PORT>`.

## Monitor the App

Show the status of the container:

```bash
docker compose ps
```

Show the log messages:

```bash
docker compose logs -f app
```

## Stop the App

Stop and remove the container:

```bash
docker compose down
```

The photos in the host directory `./photos` stay on the host.
