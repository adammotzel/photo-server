# App Configuration Setup

## Environment Variables

The app requires the following environment variables:

1. `NAME`: My dog's name, injected into the HTML templates for display.
2. `DB_PASSWORD`: The app's Postgres user password.
3. `NETWORK_NAME`: Name of the Wi-Fi network the app is running on, attributed to every prediction logged during the run.
4. `DB_HOST`: Database host. Usually just "localhost" for local dev.
5. `DB_PORT`: Database host port. Usually 5432 for Postgres.
6. `DB_USER`: App's database username.
7. `DB_NAME`: App database name.
8. `SERVER_IP`: IP for serving the app. "localhost", "0.0.0.0", etc.
9. `SERVER_PORT`: Port for serving the app.
10. `SSL_CERTFILE`: Path to SSL public cert.
11. `SSL_KEYFILE`: Path to SSL private cert.

I store these in a `.env` file at the project root.

## Test Environment Variables

Unit tests need their own `DB_NAME`, `DB_USER`, and `DB_PASSWORD`, pointing at the test database instead of the production one (see [TESTING.md](TESTING.md)). These live in a separate `.env.test` file at the project root, containing just those three keys. `tests/conftest.py` loads `.env` first, then loads `.env.test` on top with `override=True`, so test runs use the test credentials while everything else (`NAME`, `DB_HOST`, etc.) still comes from `.env`.

## Networking

I serve the app to other devices connected to trusted Wi-Fi networks. This requires allowing inbound traffic on the port for private networks (configured in my machine's firewall settings).

Other in-network devices access the app at `https://<local IP address>:<port>`.

## TLS (HTTPS)

The app is served over HTTPS using a self-signed certificate, so LAN traffic isn't sent in plaintext. Generate a cert/key pair with OpenSSL:

```
openssl req -x509 -newkey rsa:4096 -keyout $SSL_KEYFILE -out $SSL_CERTFILE -days 365 -nodes -subj "/CN=photo-server"
```

On Windows, if you run this from Git Bash specifically, MSYS mangles the `/CN=photo-server` argument into a Windows file path and the command fails. Prefix it with `MSYS_NO_PATHCONV=1` to disable that path conversion. PowerShell and other shells aren't affected.

Because the cert is self-signed, browsers on in-network devices will show a "connection not private" warning on first visit. Not ideal, but setup is minimal with this approach.
