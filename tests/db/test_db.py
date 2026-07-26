import uuid

import psycopg
import pytest

from src.db import write_photo_metadata, write_prediction

pytestmark = pytest.mark.usefixtures("db_pool")

CONTENT_TYPE = "image/jpeg"


def _unique_filename() -> str:
    """
    Generate a filename that won't collide with rows from other test runs.

    Returns
    -------
    str
        A `.jpg` filename built from a random UUID4.
    """
    return f"{uuid.uuid4()}.jpg"


def test_write_photo_metadata_returns_int_id(IP):
    """
    Verify inserting a `photos` row returns its integer primary key.

    Parameters
    ----------
    IP : str
        IP fixture, used as the uploader IP.
    """
    photo_id = write_photo_metadata(
        stored_filename=_unique_filename(),
        content_type=CONTENT_TYPE,
        uploader_ip=IP,
    )

    assert isinstance(photo_id, int)


def test_write_photo_metadata_duplicate_filename_raises(IP):
    """
    Verify inserting a second `photos` row with a filename that already
    exists raises a unique-constraint violation.

    Parameters
    ----------
    IP : str
        IP fixture, used as the uploader IP.
    """
    stored_filename = _unique_filename()

    write_photo_metadata(
        stored_filename=stored_filename,
        content_type=CONTENT_TYPE,
        uploader_ip=IP,
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        write_photo_metadata(
            stored_filename=stored_filename,
            content_type=CONTENT_TYPE,
            uploader_ip=IP,
        )


def test_write_prediction_with_valid_photo_id(IP):
    """
    Verify a prediction can be inserted referencing an existing photo id.

    Parameters
    ----------
    IP : str
        IP fixture, used as the uploader IP.
    """
    photo_id = write_photo_metadata(
        stored_filename=_unique_filename(),
        content_type=CONTENT_TYPE,
        uploader_ip=IP,
    )

    write_prediction(
        photo_id=photo_id,
        original_filename="original.jpg",
        predicted_label="dog",
        confidence=0.98,
        accepted=True,
        uploader_ip=IP,
    )


def test_write_prediction_with_null_photo_id(IP):
    """
    Verify a prediction for a rejected (non-dog) upload can be inserted with
    a null photo id.

    Parameters
    ----------
    IP : str
        IP fixture, used as the uploader IP.
    """
    write_prediction(
        photo_id=None,
        original_filename="original.jpg",
        predicted_label="cat",
        confidence=0.42,
        accepted=False,
        uploader_ip=IP,
    )
