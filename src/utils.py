import os
import tempfile

from src.db import write_photo_metadata


def save_photo(
    file_location: str,
    contents: bytes,
    stored_filename: str,
    content_type: str | None,
    user: str,
):
    """
    Write photo to disk and photo metadata to Postgres.

    Save image atomically:
        1. Write to temp file
        2. Atomically rename
        3. Write DB metadata

    This protects against race conditions. For example:
        - thread starts writing file
        - directory entry appears
        - gallery sees filename with valid extention
        - browser requests image
        - write still incomplete

    Parameters
    --------
    file_location : str
        Path used to save the photo.
    contents : bytes
        File contents.
    stored_filename : str
        File name to store in the db.
    content_type : str | None
        File content type. Optional.
    user : str
        Name of the user that uploaded the photo.
    """
    directory = os.path.dirname(file_location)

    temp_file = None

    try:
        # create temp file in SAME directory
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=directory,
            delete=False,
            suffix=".tmp",
        ) as tmp:

            temp_file = tmp.name

            tmp.write(contents)

            # ensure bytes flushed to disk
            tmp.flush()
            os.fsync(tmp.fileno())

        # atomic rename
        os.replace(temp_file, file_location)

        write_photo_metadata(
            stored_filename=stored_filename,
            content_type=content_type,
            uploaded_by=user,
        )

    except Exception:

        # cleanup temp file if it exists
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

        # cleanup final file if DB insert failed after rename
        if os.path.exists(file_location):
            os.remove(file_location)

        raise
