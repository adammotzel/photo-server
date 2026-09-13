# API

All routes are defined in `src/app.py`. Pages are server-rendered with Jinja2; there's no separate JSON API.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Home page |
| `GET` | `/upload` | Upload form page |
| `POST` | `/upload` | Accepts one or more multipart files, runs them through the upload pipeline, and re-renders the upload page with a success/partial/failure message plus a per-file breakdown of what was accepted and rejected |
| `GET` | `/photos` | Gallery page, paginated (`?page=`), newest upload first |
| `GET` | `/photos/{filename}` | Serves a single full-size photo file, with a 1-year immutable cache header |
| `GET` | `/thumbnails/{filename}` | Serves a photo's gallery thumbnail, same cache header. Falls back to the full-size original if no thumbnail exists |

## Gallery

The gallery renders thumbnails, not full-size photos, and links each tile to its original. Tiles are ~200-320px wide, so serving originals (2-11 MB each) meant a 24-photo page transferred over 100 MB. Thumbnails cut that to under 1 MB.

`write_thumbnail()` (`src/utils.py`) bounds the longest edge to 480px and encodes WebP, applying EXIF orientation so the tile matches the photo it links to. They're stored in a `thumbnails/` subfolder of `UPLOAD_FOLDER`, so they ride along with the existing bind mount.

The thumbnail route sets `media_type` explicitly, because `.webp` is missing from some platforms' mimetype registries and the guessed `application/octet-stream` makes browsers download the tile instead of rendering it.

Thumbnails are only generated at upload time.

The upload confirmation page reuses the same route and the same 480px tiles to show what was just accepted, so confirming a large batch costs a few hundred KB instead of the hundreds of MB the originals would; `loading="lazy"` leaves offscreen tiles unfetched.

## Photo Descriptions

Every accepted photo gets a short description written by an OpenAI vision model and stored in the `descriptions` table, linked from its `photos` row by `description_id` (see [DATABASE](DATABASE.md)).

The LLM call is slow, so it's fire-and-forget: `POST /upload` saves the photo and returns the results page right away, then describes the accepted photos concurrently in a FastAPI background task that runs after the response is sent. A failed description is logged and the photo simply stays without one. Shutdown waits for descriptions still in flight (see [Stopping gracefully](../setup/05_DEPLOYMENT.md#stopping-gracefully)).

The gallery holds it back until a viewer asks for it. Each tile carries its description in a `data-description` attribute, and clicking a tile opens an in-page lightbox with the full-size photo and the description beneath it. Both stay hidden behind a "Loading…" message until the original has loaded, so they appear together; Escape, the close button, or a click on the backdrop dismisses it. The description text is written into the lightbox with `textContent`, never `innerHTML`, so model-written text can't become markup.

## Startup and Shutdown

The app's `lifespan` handler opens the Postgres connection pool and starts the async logging listener on startup, and closes them on shutdown. It also sets `app.state.shutting_down = True` during shutdown, which the `POST /upload` route checks at the top of the handler and uses to reject upload requests that arrive during shutdown with a `503` rather than let them fail mid-write.

On startup, it also upserts the configured `NETWORK_NAME` into the `networks` table (inserting it if new, otherwise reusing the existing row) and caches the resulting `network_id` on `app.state`, so every prediction written during that process's lifetime is attributed to the network it was launched on.
