# App Configuration Setup

## Environment Variables

Copy `.env.example` to `.env` at the project root and fill in the values:

| Variable | Description |
| --- | --- |
| `NAME` | Pet name, injected into the HTML templates for display. |
| `NETWORK_NAME` | Wi-Fi network the app runs on, attributed to every logged prediction. |
| `DB_HOST` | Database host. `127.0.0.1` locally, `0.0.0.0` in Docker. |
| `DB_PORT` | Database port. `5432` for Postgres. |
| `DB_NAME` | Database name. |
| `DB_USER` | Database user. |
| `DB_PASSWORD` | Database user password. |
| `SERVER_IP` | IP to serve on (`localhost`, `0.0.0.0`, ...). |
| `SERVER_PORT` | Port to serve on. |
| `SSL_CERTFILE` | Path to the SSL public cert. |
| `SSL_KEYFILE` | Path to the SSL private key. |
| `OPENAI_API_KEY` | API key used to write photo descriptions. Read straight from the environment by the OpenAI SDK, not via `Config`. Optional: without it, photos are saved with no description. |

## Test Environment Variables

Unit tests run against a separate test database (see [04_TESTING.md](04_TESTING.md)). Put its `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in a `.env.test` file at the project root. `tests/conftest.py` loads `.env`, then `.env.test` with `override=True`, so only those three keys change for tests.

The tests never call OpenAI. `tests/app/conftest.py` stubs `describe_image` for every test that uploads, and the `model` suite mocks the client, so `OPENAI_API_KEY` isn't needed to run them.

## Networking

Serving the app to other LAN devices requires allowing inbound traffic on `SERVER_PORT` for private networks (via firewall settings). Devices then reach the app at `https://<local IP>:<port>`.

## TLS (HTTPS)

The app is served over HTTPS with a self-signed certificate. Generate a cert/key pair with OpenSSL:

```
openssl req -x509 -newkey rsa:4096 -keyout $SSL_KEYFILE -out $SSL_CERTFILE -days 365 -nodes -subj "/CN=photo-server"
```

On Windows Git Bash, MSYS mangles `/CN=photo-server` into a file path and the command fails. Prefix it with `MSYS_NO_PATHCONV=1`. Other shells aren't affected.

Because the cert is self-signed, browsers show a "connection not private" warning on first visit.
