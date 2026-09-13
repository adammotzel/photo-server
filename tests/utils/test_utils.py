import io
import os
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.config import THUMBNAIL_MAX_PX, THUMBNAIL_SUBDIR
from src.utils import _atomic_write, save_photo, thumbnail_path, write_thumbnail

CONTENTS = b"fake-image-bytes"
STORED_FILENAME = "photo.jpg"
CONTENT_TYPE = "image/jpeg"


def _image_bytes(size: tuple[int, int], fmt: str = "JPEG", mode: str = "RGB") -> bytes:
    """
    Render a solid-color in-memory test image.
    """
    # a fully opaque RGBA image encodes to WebP without an alpha channel, so
    # transparent test images have to actually be transparent
    color = (255, 0, 0, 128) if mode == "RGBA" else "red"

    buffer = io.BytesIO()
    Image.new(mode, size, color=color).save(buffer, format=fmt)

    return buffer.getvalue()


def test_thumbnail_path_replaces_extension():
    """
    Verify thumbnails land in the thumbnail subfolder as WebP, whatever the
    original's format.
    """
    path = thumbnail_path("photos", "abc-123.jpeg")

    assert path == os.path.join("photos", THUMBNAIL_SUBDIR, "abc-123.webp")


def test_atomic_write_cleans_up_on_failure(tmp_path):
    """
    Verify a failed write leaves neither the destination nor a temp file behind.
    """
    destination = tmp_path / "photo.jpg"

    def _fail(f):
        f.write(b"partial")
        raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        _atomic_write(str(destination), _fail)

    assert os.listdir(tmp_path) == []


def test_write_thumbnail_downscales_large_image(tmp_path):
    """
    Verify a large image is written as a WebP bounded to `THUMBNAIL_MAX_PX`,
    preserving aspect ratio.
    """
    contents = _image_bytes((3000, 2000))
    destination = tmp_path / THUMBNAIL_SUBDIR / "photo.webp"

    write_thumbnail(contents, str(destination))

    with Image.open(destination) as thumb:
        assert thumb.format == "WEBP"
        assert thumb.size == (THUMBNAIL_MAX_PX, THUMBNAIL_MAX_PX * 2 // 3)

    assert destination.stat().st_size < len(contents)


def test_write_thumbnail_does_not_upscale_small_image(tmp_path):
    """
    Verify an image already within the thumbnail bounds keeps its size.
    """
    destination = tmp_path / "small.webp"

    write_thumbnail(_image_bytes((120, 90)), str(destination))

    with Image.open(destination) as thumb:
        assert thumb.size == (120, 90)


def test_write_thumbnail_keeps_transparency(tmp_path):
    """
    Verify a transparent PNG keeps its alpha channel instead of being flattened.
    """
    destination = tmp_path / "transparent.webp"

    write_thumbnail(_image_bytes((800, 800), fmt="PNG", mode="RGBA"), str(destination))

    with Image.open(destination) as thumb:
        assert thumb.mode == "RGBA"


def test_save_photo_writes_files_and_metadata(tmp_path, monkeypatch):
    """
    Verify `save_photo` writes the original and its thumbnail, records the
    metadata, and returns the new photo id.
    """
    mock_write = MagicMock(return_value=42)
    monkeypatch.setattr("src.utils.write_photo_metadata", mock_write)

    contents = _image_bytes((2400, 1600))
    file_location = tmp_path / STORED_FILENAME
    thumbnail_location = thumbnail_path(str(tmp_path), STORED_FILENAME)

    photo_id = save_photo(
        file_location=str(file_location),
        thumbnail_location=thumbnail_location,
        contents=contents,
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )

    assert photo_id == 42
    assert file_location.read_bytes() == contents
    assert os.path.exists(thumbnail_location)
    mock_write.assert_called_once_with(
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )


def test_save_photo_survives_unrenderable_thumbnail(tmp_path, monkeypatch):
    """
    Verify the photo is still saved when its thumbnail can't be rendered.
    """
    monkeypatch.setattr("src.utils.write_photo_metadata", MagicMock(return_value=7))

    file_location = tmp_path / STORED_FILENAME
    thumbnail_location = thumbnail_path(str(tmp_path), STORED_FILENAME)

    # CONTENTS is not a decodable image
    photo_id = save_photo(
        file_location=str(file_location),
        thumbnail_location=thumbnail_location,
        contents=CONTENTS,
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )

    assert photo_id == 7
    assert file_location.read_bytes() == CONTENTS
    assert not os.path.exists(thumbnail_location)


def test_save_photo_cleans_up_on_db_failure(tmp_path, monkeypatch):
    """
    Verify the photo and thumbnail are deleted if the metadata insert fails,
    rather than left orphaned on disk.
    """
    mock_write = MagicMock(side_effect=RuntimeError("db insert failed"))
    monkeypatch.setattr("src.utils.write_photo_metadata", mock_write)

    file_location = tmp_path / STORED_FILENAME
    thumbnail_location = thumbnail_path(str(tmp_path), STORED_FILENAME)

    with pytest.raises(RuntimeError, match="db insert failed"):
        save_photo(
            file_location=str(file_location),
            thumbnail_location=thumbnail_location,
            contents=_image_bytes((1200, 1200)),
            stored_filename=STORED_FILENAME,
            content_type=CONTENT_TYPE,
        )

    assert not file_location.exists()
    assert not os.path.exists(thumbnail_location)
