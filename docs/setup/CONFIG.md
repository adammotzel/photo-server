# App Configuration Setup

## Environment Variables

The app requires the following environment variables:

1. `NAME`: My pet's name, injected into the HTML templates for display.
2. `POSTGRES_PW`: The app's Postgres user password.
3. `NETWORK_NAME`: Name of the Wi-Fi network the app is running on, attributed to every prediction logged during the run.

I store these in a `.env` file (in `src`).

## Networking

The app launches on host `0.0.0.0` and port `8000` by default.

I serve the app to other devices connected to my home (or another trusted) Wi-Fi network. This requires allowing inbound traffic on the port for private networks (configured in my machine's firewall settings).

Other in-network devices access the app at `<local IP address>:<port>`.
