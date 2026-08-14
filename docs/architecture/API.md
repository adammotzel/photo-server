# API

All routes are defined in `src/app.py`. Pages are server-rendered with Jinja2; there's no separate JSON API.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Home page |
| `GET` | `/upload` | Upload form page |
| `POST` | `/upload` | Accepts one or more multipart files, runs them through the upload pipeline (see [UPLOAD](UPLOAD.md)), and re-renders the upload page with a success/partial/failure message |
| `GET` | `/photos` | Gallery page, paginated (`?page=`), newest upload first |
| `GET` | `/photos/{filename}` | Serves a single full-size photo file, with a 1-year immutable cache header |
| `GET` | `/thumbnails/{filename}` | Serves a photo's gallery thumbnail, same cache header. Falls back to the full-size original if no thumbnail exists |

## Gallery

The gallery renders thumbnails, not full-size photos, and links each tile to its original. Tiles are ~200-320px wide, so serving originals (2-11 MB each) meant a 24-photo page transferred over 100 MB. Thumbnails cut that to under 1 MB.

`write_thumbnail()` (`src/utils.py`) bounds the longest edge to 480px and encodes WebP, applying EXIF orientation so the tile matches the photo it links to. They're stored in a `thumbnails/` subfolder of `UPLOAD_FOLDER`, so they ride along with the existing bind mount (see [CONTAINER](CONTAINER.md)).

The thumbnail route sets `media_type` explicitly, because `.webp` is missing from some platforms' mimetype registries and the guessed `application/octet-stream` makes browsers download the tile instead of rendering it.

Thumbnails are only generated at upload time.

## Startup and Shutdown

The app's `lifespan` handler opens the Postgres connection pool and starts the async logging listener on startup, and closes them on shutdown. It also sets `app.state.shutting_down = True` during shutdown, which the `POST /upload` route checks and uses to reject in-flight upload requests with a `503` rather than let them fail mid-write.

On startup, it also upserts the configured `NETWORK_NAME` into the `networks` table (inserting it if new, otherwise reusing the existing row) and caches the resulting `network_id` on `app.state`, so every prediction written during that process's lifetime is attributed to the network it was launched on.
