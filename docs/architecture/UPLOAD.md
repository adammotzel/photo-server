# Upload Flow

`POST /upload` (`src/app.py`) accepts a batch of files and processes each one independently through `_process_upload`, run concurrently via `asyncio.gather`. Per file:

1. **Extension/MIME check**: the file extension and content type are checked against an allow-list (`ALLOWED_EXTENSIONS`, `ALLOWED_MIME_TYPES` in `src/config.py`). Anything outside the list is rejected immediately, without a `predictions` row.
2. **Classification**: the file's bytes are read into memory and passed to `inference()` (`src/model.py`), offloaded to a worker thread with `run_in_threadpool` since model inference is CPU-bound and would otherwise block the event loop.
3. **Reject path**: if the predicted label isn't `"dog"`, a `predictions` row is written with `photo_id = NULL` and the file is discarded without ever touching disk. This keeps a record of every rejected upload for monitoring the classifier, without storing the image itself.
4. **Accept path**: if the predicted label is `"dog"`, `save_photo()` (`src/utils.py`) writes the file to disk atomically before writing the `photos` row. Writing the file before the DB row exists prevents the gallery from listing a photo that isn't fully written yet.
5. **Prediction logging**: a `predictions` row is written referencing the new `photo_id`, completing the record for that upload.

Every accepted upload ends up with exactly one `photos` row and one `predictions` row; every rejected upload gets only a `predictions` row. See [DATABASE](DATABASE.md) for the schema.

`POST /upload` itself reports back to the user based on how many of the batch succeeded: all rejected, some rejected (partial success), or all accepted.
