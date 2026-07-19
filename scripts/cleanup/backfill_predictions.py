"""
One-time script. Backfill the 'predictions' table for photos that were
uploaded before predictions were tracked.

```python
python -m scripts.cleanup.backfill_predictions
```
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from src.model import inference

load_dotenv()

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photoapp",
    "user": "photoapp_user",
    "password": os.getenv("POSTGRES_PW"),
}

PHOTO_DIR = Path("src/photos")

SELECT_MISSING_SQL = """
SELECT p.id, p.stored_filename, p.uploader_ip
FROM photos p
LEFT JOIN predictions pr ON pr.photo_id = p.id
WHERE pr.id IS NULL
"""

INSERT_PREDICTION_SQL = """
INSERT INTO predictions (
    photo_id,
    original_filename,
    predicted_label,
    confidence,
    accepted,
    uploader_ip
)
VALUES (%s, %s, %s, %s, %s, %s)
"""


def main():
    conn = psycopg.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SELECT_MISSING_SQL)
    rows = cur.fetchall()

    print(f"Found {len(rows)} photo(s) without a prediction record")

    backfilled_count = 0

    for photo_id, stored_filename, uploader_ip in rows:
        file_path = PHOTO_DIR / stored_filename

        if not file_path.is_file():
            print(f"Missing file: {stored_filename} -> skipping")
            continue

        try:
            contents = file_path.read_bytes()
            predicted_label, confidence = inference(contents)

            cur.execute(
                INSERT_PREDICTION_SQL,
                (
                    photo_id,
                    stored_filename,
                    predicted_label,
                    confidence,
                    True,
                    uploader_ip,
                ),
            )
            conn.commit()

            backfilled_count += 1
            print(f"Backfilled: {stored_filename} -> {predicted_label} ({confidence:.4f})")

        except Exception as e:
            conn.rollback()
            print(f"ERROR processing {stored_filename}: {e}")

    cur.close()
    conn.close()

    print(f"Backfill complete. {backfilled_count} record(s) added.")


if __name__ == "__main__":
    main()
