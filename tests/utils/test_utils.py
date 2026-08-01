import os
from unittest.mock import MagicMock

import pytest

from src.utils import save_photo

CONTENTS = b"fake-image-bytes"
STORED_FILENAME = "photo.jpg"
CONTENT_TYPE = "image/jpeg"


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
        contents=CONTENTS,
        stored_filename=STORED_FILENAME,
        content_type=CONTENT_TYPE,
    )

    assert photo_id == 42
    assert file_location.read_bytes() == CONTENTS


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
    Verify `save_photo` deletes the file it wrote if the metadata insert
    fails, instead of leaving an orphaned file on disk.

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

    with pytest.raises(RuntimeError, match="db insert failed"):
        save_photo(
            file_location=str(file_location),
            contents=CONTENTS,
            stored_filename=STORED_FILENAME,
            content_type=CONTENT_TYPE,
        )

    assert os.listdir(tmp_path) == []
