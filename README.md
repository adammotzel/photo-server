# Photo Server

A side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi.

## App Features

- Open access on trusted Wi-Fi networks (e.g., my home Wi-Fi), no accounts or login required
- Ability for users to upload new photos, automatically attributed to the uploading device's LAN IP address (for tracking photo metadata)
- Ability for users to view all uploaded photos in a "gallery"
- An image verification layer (using the `efficientnet-b0` vision model)

## Software + Tools

Language:
- Python 3.12+

Dependency Management:
- `uv` + `pyproject.toml`

Backend Services:
- PostgreSQL

Containerization:
- Docker + compose

Security:
- OpenSSL (self-signed TLS certs)

## Architecture Decisions

### FastAPI Backend

FastAPI is my default Python web framework. It's just really easy to use.

The endpoints are defined as async, but most core app functions are written synchronously. I use FastAPI's `run_in_threadpool` utility to offload blocking operations to worker threads. It works well for an app of this size.

### Vanilla HTML Frontend

It's a simple app, and basic HTML works fine for serving static web pages. Maybe someday I'll implement a heavier frontend framework for fun.

### PostgreSQL Database Backend

Postgres is simple to set up and use. It's only utilized for storing uploaded photo metadata, including the uploading device's LAN IP address, and the classifier's predictions. The photos themselves are just stored on disk.

I chose to use `psycopg` for database interactions. It's lighter and faster than an ORM like SQLAlchemy, and since I only have three database tables (photos, predictions, and a small networks lookup table), an ORM felt like overkill.

### Image Verification Layer

Google's `efficientnet-b0` vision model offers solid accuracy and low resource consumption. It works great for a small app served on CPU.

### Security

This app is only served on trusted Wi-Fi (LAN), never exposed to the internet. Traffic is still encrypted over HTTPS using a self-signed cert; in-network devices see a one-time browser warning since the cert isn't from a trusted CA. See [docs/setup/02_CONFIG.md](docs/setup/02_CONFIG.md) for cert setup.

## Documentation

See [docs/architecture](docs/architecture) for a deeper architecture breakdown and [docs/setup](docs/setup) for app configuration details.

## Deployment

The app can be deployed directly from host or from a Docker container.

Build and run using Docker:
```bash
bash scripts/build.sh
docker compose up -d
```

`scripts/build.sh` only builds from a clean `main` checkout, so every image maps back to one commit. It runs `docker compose build` and sets `PHOTO_SERVER_TAG` in `.env` to the tag it just built, which is what `docker compose` runs. See [docs/architecture/CONTAINER.md](docs/architecture/CONTAINER.md) for details.

Run from host:
```python
uv run --no-sync python -m scripts.run
```

Both options assume the [setup](docs/setup) instructions have been followed.
