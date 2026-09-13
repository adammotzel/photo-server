import uuid

import psycopg
import pytest

from src.db import (
    get_photos,
    pool,
    upsert_network,
    write_description,
    write_photo_metadata,
    write_prediction,
)

pytestmark = pytest.mark.usefixtures("db_pool")

CONTENT_TYPE = "image/jpeg"


def _unique_filename() -> str:
    """
    A `.jpg` filename that won't collide with rows from other test runs.
    """
    return f"{uuid.uuid4()}.jpg"


def _get_photo(stored_filename: str):
    """
    Find a just-written photo among the newest page returned by `get_photos`.
    """
    return next(
        photo for photo in get_photos(limit=100, offset=0)
        if photo.stored_filename == stored_filename
    )


def test_write_photo_metadata_duplicate_filename_raises():
    """
    Verify stored filenames are unique across `photos` rows.
    """
    stored_filename = _unique_filename()
    write_photo_metadata(stored_filename=stored_filename, content_type=CONTENT_TYPE)

    with pytest.raises(psycopg.errors.UniqueViolation):
        write_photo_metadata(stored_filename=stored_filename, content_type=CONTENT_TYPE)


def test_write_description_links_existing_photo():
    """
    Verify a description written for an already-saved photo survives the
    round trip through the gallery query's join.
    """
    stored_filename = _unique_filename()
    photo_id = write_photo_metadata(
        stored_filename=stored_filename, content_type=CONTENT_TYPE
    )
    description = f"Description {uuid.uuid4()}"

    write_description(
        photo_id=photo_id,
        description=description,
        input_tokens=100,
        output_tokens=20,
        model="test-model",
    )

    assert _get_photo(stored_filename).description == description


def test_write_description_for_missing_photo_writes_nothing():
    """
    Verify a description for a nonexistent photo raises and rolls back its
    insert, rather than leaving a `descriptions` row no photo points to.
    """
    description = f"Description {uuid.uuid4()}"

    # identity ids start at 1, so -1 never matches a row
    with pytest.raises(RuntimeError):
        write_description(
            photo_id=-1,
            description=description,
            input_tokens=100,
            output_tokens=20,
            model="test-model",
        )

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM descriptions WHERE description = %s",
                (description,),
            )
            assert cur.fetchone() == (0,)


def test_get_photos_description_defaults_to_none():
    """
    Verify a photo without a description comes back with `None`, rather than
    being dropped by the gallery query's join.
    """
    stored_filename = _unique_filename()
    write_photo_metadata(stored_filename=stored_filename, content_type=CONTENT_TYPE)

    assert _get_photo(stored_filename).description is None


@pytest.mark.parametrize("accepted", [True, False], ids=["accepted", "rejected"])
def test_write_prediction(accepted):
    """
    Verify predictions are recorded both for accepted uploads (linked to a
    photo) and rejected ones (no photo).
    """
    photo_id = None
    if accepted:
        photo_id = write_photo_metadata(
            stored_filename=_unique_filename(),
            content_type=CONTENT_TYPE,
        )
    original_filename = _unique_filename()

    write_prediction(
        photo_id=photo_id,
        network_id=None,
        original_filename=original_filename,
        predicted_label="dog" if accepted else "cat",
        confidence=0.9,
        uploader_ip="127.0.0.1",
    )

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id FROM predictions WHERE original_filename = %s",
                (original_filename,),
            )
            assert cur.fetchone() == (photo_id,)


def test_upsert_network_is_idempotent():
    """
    Verify upserting the same network name twice returns the same id rather
    than creating a duplicate row.
    """
    name = f"test-network-{uuid.uuid4()}"

    assert upsert_network(name) == upsert_network(name)
