"""
One-time script. Migrate JSON meta-data files to Postgres.

You'll need a .env file in this directory with one secret, POSTGRES_PW.
"""

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

POSRGRES_APP_PW = os.getenv("POSTGRES_PW")
PHOTO_DIR = Path("src/photos")

DB_CONN_INFO = (
    "dbname=photoapp "
    "user=photoapp_user "
    "password={} "
    "host=localhost "
    "port=5432"
).format(POSRGRES_APP_PW)

INSERT_PHOTO_SQL = """
INSERT INTO photos (
    stored_filename,
    content_type,
    uploaded_by,
    uploaded_at
)
VALUES (%s, %s, %s, %s)
ON CONFLICT (stored_filename) DO NOTHING
"""


def main():
    json_files = list(PHOTO_DIR.glob("*.json"))

    print(f"Found {len(json_files)} metadata files")

    with psycopg.connect(DB_CONN_INFO) as conn:
        with conn.cursor() as cur:

            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    stored_filename = metadata["original_filename"]
                    content_type = metadata.get("content_type")
                    uploaded_by = metadata["uploaded_by"]
                    uploaded_at = metadata["uploaded_time"]

                    cur.execute(
                        INSERT_PHOTO_SQL,
                        (
                            stored_filename,
                            content_type,
                            uploaded_by,
                            uploaded_at,
                        ),
                    )

                    print(f"Inserted: {stored_filename}")

                except Exception as e:
                    print(f"ERROR processing {json_file}: {e}")

        conn.commit()

    print("Migration complete")


if __name__ == "__main__":
    main()
