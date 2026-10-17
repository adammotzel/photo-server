"""
Backfill descriptions for photos that don't have one.

Finds every 'photos' record with a null 'description_id', sends the photo on
disk to OpenAI, and links the new description to it. With --reset, every
photo is re-described instead, overwriting its existing 'descriptions' row in
place. Run from the repo root against the database in `.env`:

    uv run python scripts/describe_photos.py [--reset] [--limit N] [--dry-run]
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

# must run before any `src.*` import, since src/config.py builds Config() at
# import time
load_dotenv(ROOT_DIR / ".env")
sys.path.insert(0, str(ROOT_DIR))

from src.config import UPLOAD_FOLDER  # noqa: E402
from src.db import pool, write_description  # noqa: E402
from src.model import describe_image  # noqa: E402
from src.types import Description  # noqa: E402


def get_photos_to_describe(reset: bool, limit: int | None) -> list[tuple[int, str]]:
    """
    Fetch photos to describe, oldest upload first.

    Parameters
    ----------
    reset : bool
        Include photos that already have a description, to replace it.
    limit : int | None
        Maximum number of photos to return, or None for all of them.

    Returns
    -------
    list[tuple[int, str]]
        'id' and stored filename of each photo.
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, stored_filename
                FROM photos
                WHERE description_id IS NULL OR %s
                ORDER BY uploaded_at, id
                LIMIT %s
                """,
                (reset, limit),
            )
            return cur.fetchall()


def upsert_description(photo_id: int, description: Description) -> None:
    """
    Overwrite the photo's linked 'descriptions' row, or insert and link a new
    one if it has none.

    Parameters
    ----------
    photo_id : int
        'id' of the 'photos' record the description belongs to.
    description : Description
        The new description and its token usage and model.

    Returns
    -------
    None
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE descriptions d
                SET description = %s,
                    input_tokens = %s,
                    output_tokens = %s,
                    model = %s,
                    generated_at = NOW()
                FROM photos p
                WHERE p.id = %s
                  AND d.id = p.description_id
                """,
                (*description, photo_id),
            )
            if cur.rowcount == 1:
                return

    write_description(photo_id, *description)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--limit", type=int, help="describe at most N photos")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="re-describe every photo, overwriting existing descriptions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the photos that would be described, without calling OpenAI",
    )
    args = parser.parse_args()

    pool.open()

    try:
        photos = get_photos_to_describe(args.reset, args.limit)
        print(f"Found {len(photos)} photo(s) to describe.")

        described = failed = 0
        input_tokens = output_tokens = 0

        for i, (photo_id, stored_filename) in enumerate(photos, start=1):
            prefix = f"[{i}/{len(photos)}] {stored_filename}"
            path = ROOT_DIR / UPLOAD_FOLDER / stored_filename

            if not path.exists():
                print(f"{prefix}: file not found, skipping")
                failed += 1
                continue

            if args.dry_run:
                print(f"{prefix}: would describe")
                continue

            # one bad photo shouldn't stop the rest; re-running retries it
            try:
                description = describe_image(path.read_bytes())
                upsert_description(photo_id, description)
            except Exception as e:
                print(f"{prefix}: failed ({e})")
                failed += 1
                continue

            described += 1
            input_tokens += description.input_tokens
            output_tokens += description.output_tokens
            print(f"{prefix}: {description.description}")

        if not args.dry_run:
            print(
                f"Described {described}, failed {failed}. "
                f"Tokens: {input_tokens} in, {output_tokens} out."
            )
    finally:
        pool.close()


if __name__ == "__main__":
    main()
