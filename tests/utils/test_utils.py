import io
import os
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.constants import THUMBNAIL_MAX_PX, THUMBNAIL_SUBDIR
from src.utils import save_photo, thumbnail_path, write_thumbnail

CONTENTS = b"fake-image-bytes"
STORED_FILENAME = "photo.jpg"
CONTENT_TYPE = "image/jpeg"


def _image_bytes(size: tuple[int, int], fmt: str = "JPEG", mode: str = "RGB") -> bytes:
    """
    Render an in-memory test image.

    Parameters
    ----------
    size : tuple[int, int]
        Width and height of the generated image, in pixels.
    fmt : str
        Pillow format to encode as.
    mode : str
        Pillow color mode of the generated image.

    Returns
    -------
    bytes
        Encoded image bytes.
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
    original's format was.
    """
    path = thumbnail_path("photos", "abc-123.jpeg")

    assert path == os.path.join("photos", THUMBNAIL_SUBDIR, "abc-123.webp")


def test_write_thumbnail_downscales_large_image(tmp_path):
    """
    Verify `write_thumbnail` bounds the longest edge and produces a file far
    smaller than the original.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    """
    contents = _image_bytes((3000, 2000))
    destination = tmp_path / THUMBNAIL_SUBDIR / "photo.webp"

    write_thumbnail(contents, str(destination))

    with Image.open(destination) as thumb:
        assert thumb.format == "WEBP"
        assert max(thumb.size) == THUMBNAIL_MAX_PX
        assert thumb.size == (THUMBNAIL_MAX_PX, THUMBNAIL_MAX_PX * 2 // 3)

    assert destination.stat().st_size < len(contents)


def test_write_thumbnail_leaves_small_image_within_bounds(tmp_path):
    """
    Verify an image already smaller than the thumbnail box is not upscaled.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    """
    destination = tmp_path / "small.webp"

    write_thumbnail(_image_bytes((120, 90)), str(destination))

    with Image.open(destination) as thumb:
        assert thumb.size == (120, 90)


def test_write_thumbnail_keeps_transparency(tmp_path):
    """
    Verify a transparent PNG keeps its alpha channel instead of being
    flattened onto an opaque background.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    """
    contents = _image_bytes((800, 800), fmt="PNG", mode="RGBA")
    destination = tmp_path / "transparent.webp"

    write_thumbnail(contents, str(destination))

    with Image.open(destination) as thumb:
        assert thumb.mode == "RGBA"


def test_write_thumbnail_leaves_no_temp_files_behind(tmp_path):
    """
    Verify the atomic write cleans up after itself, leaving only the finished
    thumbnail in the directory.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    """
    destination = tmp_path / "photo.webp"

    write_thumbnail(_image_bytes((900, 900)), str(destination))

    assert os.listdir(tmp_path) == ["photo.webp"]


def test_save_photo_writes_file_and_returns_id(tmp_path, monkeypatch):
    """
    Verify `save_photo` writes the file to disk and returns the id from
    the (mocked) metadata insert.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to replace `src.utils.write_photo_metadata`
        with a mock.
    """
    mock_write = MagicMock(return_value=42)
    monkeypatch.setattr("src.utils.write_photo_metadata", mock_write)

    file_location = tmp_path / STORED_FILENAME

    photo_id = save_photo(
        file_location=str(file_location),
        thumbnail_location=thumbnail_path(str(tmp_path), STORED_FILENAME),
        contents=CONTENTS,
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )

    assert photo_id == 42
    assert file_location.read_bytes() == CONTENTS


def test_save_photo_writes_thumbnail(tmp_path, monkeypatch):
    """
    Verify a successful upload also leaves a downscaled thumbnail on disk.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to replace `src.utils.write_photo_metadata`
        with a mock.
    """
    monkeypatch.setattr("src.utils.write_photo_metadata", MagicMock(return_value=1))

    contents = _image_bytes((2400, 1600))
    thumbnail_location = thumbnail_path(str(tmp_path), STORED_FILENAME)

    save_photo(
        file_location=str(tmp_path / STORED_FILENAME),
        thumbnail_location=thumbnail_location,
        contents=contents,
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )

    assert os.path.exists(thumbnail_location)
    assert os.path.getsize(thumbnail_location) < len(contents)


def test_save_photo_survives_unrenderable_thumbnail(tmp_path, monkeypatch):
    """
    Verify an upload still succeeds when the thumbnail can't be rendered, so
    a bad decode never costs the user their photo.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to replace `src.utils.write_photo_metadata`
        with a mock.
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


def test_save_photo_passes_correct_metadata_to_db(tmp_path, monkeypatch):
    """
    Verify `save_photo` forwards the correct metadata to
    `write_photo_metadata`.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to replace `src.utils.write_photo_metadata`
        with a mock.
    """
    mock_write = MagicMock(return_value=1)
    monkeypatch.setattr("src.utils.write_photo_metadata", mock_write)

    file_location = tmp_path / STORED_FILENAME

    save_photo(
        file_location=str(file_location),
        thumbnail_location=thumbnail_path(str(tmp_path), STORED_FILENAME),
        contents=CONTENTS,
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )

    mock_write.assert_called_once_with(
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )


def test_save_photo_cleans_up_on_db_failure(tmp_path, monkeypatch):
    """
    Verify `save_photo` deletes the photo and thumbnail it wrote if the
    metadata insert fails, instead of leaving orphaned files on disk.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to replace `src.utils.write_photo_metadata`
        with a mock that raises.
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
    assert os.listdir(tmp_path) == [THUMBNAIL_SUBDIR]
