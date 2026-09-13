# Database Design

Postgres just stores metadata. The photos themselves live on disk. 

There are four database tables, with no ORM. I write raw SQL using `psycopg` (see [docs/setup/01_POSTGRES.md](../setup/01_POSTGRES.md) for setup).

## Tables

| Table | Description |
|---|---|
| `photos` | One row per accepted photo upload. Contains the on-disk filename and a reference (`description_id`) to the photo's description |
| `descriptions` | One row per LLM-written photo description, shown when a viewer opens the photo. Also stores the token usage and model name of the call that wrote it, for tracking API spend |
| `predictions` | One row per upload that reaches the classifier, accepted or rejected. Logs the classifier's prediction and confidence, which lets me monitor its behavior over time, not just the uploads it accepted. Uploads rejected earlier by the extension/MIME allow-list never get a row. Also stores the uploader's LAN IP and a reference (`network_id`) to the active Wi-Fi network |
| `networks` | Lookup table of Wi-Fi networks. Upserted once per process at startup (from `NETWORK_NAME`) and referenced by `predictions` to attribute each prediction to the uploader network |

## Schemas

### `photos`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `stored_filename` | TEXT | No | Unique, UUID-based filename of the photo on disk |
| `content_type` | TEXT | Yes | MIME type of the upload |
| `description_id` | INT | Yes | References `descriptions(id)`, `ON DELETE SET NULL`. Set after insert, once the background description finishes. Null until then, for photos uploaded before descriptions existed, and for those whose description failed to generate |
| `uploaded_at` | TIMESTAMPTZ | No | Defaults to `NOW()` |

### `descriptions`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | INT (identity) | No | Primary key, auto-generated |
| `description` | TEXT | No | LLM-written description of the photo, revealed when a viewer opens its tile |
| `input_tokens` | INT | No | Tokens billed for the prompt, including the image |
| `output_tokens` | INT | No | Tokens billed for the description |
| `generated_at` | TIMESTAMPTZ | No | Defaults to `NOW()` |
| `model` | TEXT | No | Model that wrote the description, as reported by the API |

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
