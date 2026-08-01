# Database Design

Postgres stores metadata only; the photos themselves live on disk (see [UPLOAD](UPLOAD.md)). There are three tables, with no ORM in front of them. I write raw SQL through `psycopg` (see [docs/setup/POSTGRES.md](../setup/POSTGRES.md) for the DDL and grants).

## Tables

| Table | Description |
|---|---|
| `photos` | One row per accepted photo upload. Holds the on-disk filename |
| `predictions` | One row per upload attempt, accepted or rejected. Logs the classifier's prediction and confidence for every image sent to the app, which lets me monitor the classifier's behavior over time, not just the uploads it let through. Also stores the uploader's LAN IP and the active Wi-Fi network name |
| `networks` | Lookup table of Wi-Fi networks the app has been deployed on. Upserted once per process at startup (from `NETWORK_NAME`) and referenced by `predictions` to attribute each prediction to the network it came in on |

## Schemas

### `photos`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `stored_filename` | TEXT | No | Unique, UUID-based filename the photo is saved under on disk |
| `content_type` | TEXT | Yes | MIME type of the upload |
| `uploaded_at` | TIMESTAMPTZ | No | Defaults to `NOW()` |

### `predictions`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `photo_id` | INT | Yes | References `photos(id)`, `ON DELETE SET NULL`. Null when the upload was rejected, since rejected images are never saved to `photos`; `ON DELETE SET NULL` keeps prediction history intact if a photo is later removed |
| `network_id` | INT | Yes | References `networks(id)`, `ON DELETE SET NULL`. Set once per process at startup from `NETWORK_NAME` |
| `original_filename` | TEXT | No | Filename as uploaded, before it's renamed for storage |
| `predicted_label` | TEXT | No | Label the classifier assigned to the image |
| `confidence` | REAL | No | Classifier's confidence score for the predicted label |
| `uploader_ip` | TEXT | No | LAN IP address of the uploading device |
| `predicted_at` | TIMESTAMPTZ | No | Defaults to `NOW()` |

### `networks`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `name` | TEXT | No | Unique. Name of the Wi-Fi network; the app's upsert key on startup |
