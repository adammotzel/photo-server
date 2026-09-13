import io
import os
import tempfile
from typing import IO, Callable

from PIL import Image, ImageOps

from src.config import THUMBNAIL_MAX_PX, THUMBNAIL_QUALITY, THUMBNAIL_SUBDIR
from src.db import write_photo_metadata
from src.logger import logger


def _atomic_write(file_location: str, write: Callable[[IO[bytes]], object]) -> None:
    """
    Write a file to disk atomically:
        1. Write to temp file in the same directory
        2. Flush to disk
        3. Atomically rename

    This protects against race conditions. For example:
        - thread starts writing file
        - directory entry appears
        - gallery sees filename with valid extention
        - browser requests image
        - write still incomplete

    Parameters
    ----------
    file_location : str
        Final path of the file.
    write : Callable[[IO[bytes]], object]
        Callback that writes the file contents to the open temp file.

    Returns
    -------
    None
    """
    directory = os.path.dirname(file_location) or "."

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

            write(tmp)

            # ensure bytes flushed to disk
            tmp.flush()
            os.fsync(tmp.fileno())

        # atomic rename
        os.replace(temp_file, file_location)

    except Exception:

        # cleanup temp file if it exists
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

        raise


def thumbnail_path(upload_folder: str, stored_filename: str) -> str:
    """
    Build the on-disk path of a photo's thumbnail.

    Thumbnails are always WebP, regardless of the original's format, so the
    stored filename's extension is replaced rather than kept.

    Parameters
    ----------
    upload_folder : str
        Directory the original photos are stored in.
    stored_filename : str
        Name of the original file on disk.

    Returns
    -------
    str
        Path to the thumbnail for `stored_filename`.
    """
    stem = os.path.splitext(os.path.basename(stored_filename))[0]

    return os.path.join(upload_folder, THUMBNAIL_SUBDIR, f"{stem}.webp")


def write_thumbnail(contents: bytes, thumbnail_location: str) -> None:
    """
    Downscale an image and write it to disk as a WebP thumbnail.

    Parameters
    ----------
    contents : bytes
        Contents of the original image file.
    thumbnail_location : str
        Path used to save the thumbnail.

    Returns
    -------
    None
    """
    os.makedirs(os.path.dirname(thumbnail_location) or ".", exist_ok=True)

    with Image.open(io.BytesIO(contents)) as img:

        # browsers apply EXIF orientation to the original, so a thumbnail
        # written without it would hang in the gallery rotated differently
        # than the full-size photo it links to
        image = ImageOps.exif_transpose(img) or img

        if image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        ):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        image.thumbnail(
            (THUMBNAIL_MAX_PX, THUMBNAIL_MAX_PX),
            Image.Resampling.LANCZOS,
        )

        _atomic_write(
            thumbnail_location,
            lambda f: image.save(f, format="WEBP", quality=THUMBNAIL_QUALITY),
        )


def save_photo(
    file_location: str,
    thumbnail_location: str,
    contents: bytes,
    stored_filename: str,
    content_type: str | None,
) -> int:
    """
    Write photo and its gallery thumbnail to disk, and photo metadata to
    Postgres.

    Both files are written atomically (see `_atomic_write`). A thumbnail that
    fails to render is logged and skipped rather than failing the upload; the
    gallery falls back to serving the original in that case.

    Parameters
    --------
    file_location : str
        Path used to save the photo.
    thumbnail_location : str
        Path used to save the photo's thumbnail.
    contents : bytes
        File contents.
    stored_filename : str
        File name to store in the db.
    content_type : str | None
        File content type. Optional.

    Returns
    -------
    int
        The 'id' of the new photo record.
    """

    try:
        _atomic_write(file_location, lambda f: f.write(contents))

        try:
            write_thumbnail(contents, thumbnail_location)
        except Exception:
            logger.warning(
                f"Failed to write a thumbnail for '{stored_filename}'; "
                "the gallery will serve the original.",
                exc_info=True,
            )

        return write_photo_metadata(
            stored_filename=stored_filename,
            content_type=content_type,
        )

    except Exception:

        # cleanup files if the DB insert failed after rename
        for path in (file_location, thumbnail_location):
            if os.path.exists(path):
                os.remove(path)

        raise
