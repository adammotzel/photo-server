# App Configuration Setup

## Environment Variables

The app requires the following environment variables:

1. `NAME`: My pet's name, injected into the HTML templates for display.
2. `POSTGRES_PW`: The app's Postgres user password.
3. `NETWORK_NAME`: Name of the Wi-Fi network the app is running on, attributed to every prediction logged during the run.
4. `DB_HOST`: Postrgres host. Usually "localhost".
5. `DB_PORT`: Postgres host port. Usually 5432.
6. `DB_USER`: App's database username. For this project, "photoapp_user".
7. `DB_NAME`: App database name. For this project, "photoapp".
8. `TEST_DB_NAME`: App's test database name. For this project, "photoapp_test".

I store these in a `.env` file (in `src`).

## Networking

The app launches on host `0.0.0.0` and port `8000` by default.

I serve the app to other devices connected to trusted Wi-Fi networks. This requires allowing inbound traffic on the port for private networks (configured in my machine's firewall settings).

Other in-network devices access the app at `<local IP address>:<port>`.
