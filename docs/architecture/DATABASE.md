# Database Design

Postgres just stores metadata. The photos themselves live on disk (see [UPLOAD](UPLOAD.md)). 

There are three database tables, with no ORM. I write raw SQL using `psycopg` (see [docs/setup/01_POSTGRES.md](../setup/01_POSTGRES.md) for setup).

## Tables

| Table | Description |
|---|---|
| `photos` | One row per accepted photo upload. Contains the on-disk filename |
| `predictions` | One row per upload attempt, accepted or rejected. Logs the classifier's prediction and confidence for every image sent to the app, which lets me monitor the classifier's behavior over time, not just the uploads it accepted. Also stores the uploader's LAN IP and the active Wi-Fi network name |
| `networks` | Lookup table of Wi-Fi networks. Upserted once per process at startup (from `NETWORK_NAME`) and referenced by `predictions` to attribute each prediction to the uploader network |

## Schemas

### `photos`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `stored_filename` | TEXT | No | Unique, UUID-based filename of the photo on disk |
| `content_type` | TEXT | Yes | MIME type of the upload |
| `uploaded_at` | TIMESTAMPTZ | No | Defaults to `NOW()` |

### `predictions`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `photo_id` | INT | Yes | References `photos(id)`, `ON DELETE SET NULL`. Null when the upload was rejected, since rejected images are never saved to `photos`; `ON DELETE SET NULL` keeps prediction history intact if a photo is later removed |
| `network_id` | INT | Yes | References `networks(id)`, `ON DELETE SET NULL`. Set once per process at startup from `NETWORK_NAME` |
| `original_filename` | TEXT | No | Filename as uploaded, before it's renamed for storage |
| `predicted_label` | TEXT | No | Classifier prediction |
| `confidence` | REAL | No | Classifier's confidence score for the prediction |
| `uploader_ip` | TEXT | No | LAN IP address of the uploading device |
| `predicted_at` | TIMESTAMPTZ | No | Defaults to `NOW()` |

### `networks`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `name` | TEXT | No | Unique. Name of the Wi-Fi network |
