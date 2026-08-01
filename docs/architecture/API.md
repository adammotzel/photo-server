# API

All routes are defined in `src/app.py`. Pages are server-rendered with Jinja2; there's no separate JSON API.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Home page |
| `GET` | `/upload` | Upload form page |
| `POST` | `/upload` | Accepts one or more multipart files, runs them through the upload pipeline (see [UPLOAD](UPLOAD.md)), and re-renders the upload page with a success/partial/failure message |
| `GET` | `/photos` | Gallery page, lists every photo currently in `src/photos/` |
| `GET` | `/photos/{filename}` | Serves a single photo file, with a 1-year immutable cache header |

## Startup and Shutdown

The app's `lifespan` handler opens the Postgres connection pool and starts the async logging listener on startup, and closes them on shutdown. It also sets `app.state.shutting_down = True` during shutdown, which the `POST /upload` route checks and uses to reject in-flight upload requests with a `503` rather than let them fail mid-write.

On startup, it also upserts the configured `NETWORK_NAME` into the `networks` table (inserting it if new, otherwise reusing the existing row) and caches the resulting `network_id` on `app.state`, so every prediction written during that process's lifetime is attributed to the network it was launched on.
