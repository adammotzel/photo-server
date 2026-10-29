# Photo Server

A side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi.

## App Features

- Open access on trusted Wi-Fi networks (e.g., my home Wi-Fi), no accounts or login required
- Ability for users to upload new photos, each receiving an LLM generated description
- An image verification layer (using the `efficientnet-b0` vision model)
- Ability for users to view all uploaded photos in a "gallery", where clicking a photo reveals an LLM-written description of it

## Software + Tools

Language:
- Python 3.12+

Dependency Management:
- `uv` + `pyproject.toml`

Backend Services:
- PostgreSQL
- OpenAI API (photo descriptions)

Containerization:
- Docker + compose

Security:
- OpenSSL (self-signed TLS certs)

## Quick Start

First, install PostgreSQL and `uv`. Then follow the [setup](docs/setup) instructions and launch the app locally:

```bash
uv run --no-sync python -m scripts.run
```

In-network devices can access the app at `https://<host LAN IP>:<SERVER_PORT>`.

## Architecture Decisions

### Python FastAPI Backend

FastAPI is my default Python web framework. It's just really easy to use.

The endpoints are defined as async, but core app functions are written synchronously. I use FastAPI's `run_in_threadpool` utility to offload blocking operations to worker threads. It works well for an app of this size.

### Vanilla HTML Frontend

It's a simple app, and basic HTML (with some embedded JavaScript) works fine for serving the web pages. Maybe someday I'll implement a heavier frontend framework for fun.

### PostgreSQL Database

Postgres is simple to set up and use. It's only utilized for storing uploaded photo metadata, including the uploading device's LAN IP address, the classifier's predictions, and photo descriptions. The photos themselves are just stored on disk.

I use SQLAlchemy as the ORM and Alembic for migrations. I originally chose to just use `psycopg` for database interactions (without an ORM) because it's lighter and faster, but as the project grew, using an ORM became a better option.

### Image Verification Layer

Google's `efficientnet-b0` vision model offers solid accuracy and low resource consumption. It works great for a small app served on CPU.

### Security

This app is only served on trusted Wi-Fi (LAN), never exposed to the internet. Traffic is still encrypted over HTTPS using a self-signed cert; in-network devices see a one-time browser warning since the cert isn't from a trusted CA. See [docs/setup/01_CONFIG.md](docs/setup/01_CONFIG.md) for cert setup.

## Documentation

See [docs/architecture](docs/architecture) for a deeper architecture breakdown and [docs/setup](docs/setup) for app configuration details.
