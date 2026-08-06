import uuid
from unittest.mock import MagicMock

import pytest

from src.constants import NAME
from src.db import pool

pytestmark = pytest.mark.usefixtures("db_pool")


def _fetch_prediction(original_filename: str):
    """
    Look up a `predictions` row by the original uploaded filename.

    Parameters
    ----------
    original_filename : str
        Filename as submitted by the uploading client, matched against
        `predictions.original_filename`.

    Returns
    -------
    tuple | None
        `(photo_id, predicted_label)` for the matching row, or `None` if no
        row was found.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id, predicted_label "
                "FROM predictions WHERE original_filename = %s",
                (original_filename,),
            )
            return cur.fetchone()


def _fetch_photo_stored_filename(photo_id: int):
    """
    Look up the stored filename for a `photos` row by its id.

    Parameters
    ----------
    photo_id : int
        Primary key of the `photos` row to look up.

    Returns
    -------
    str | None
        The `stored_filename` value for the matching row, or `None` if no
        row was found.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT stored_filename FROM photos WHERE id = %s", (photo_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None


def test_read_root(client):
    """
    Verify the home page loads and displays the configured app name.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    """
    response = client.get("/")

    assert response.status_code == 200
    assert NAME in response.text


def test_upload_form(client):
    """
    Verify the upload form page loads successfully.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    """
    response = client.get("/upload")

    assert response.status_code == 200


def test_upload_accepted_dog_photo(
    client, 
    upload_dir, 
    force_inference, 
    sample_image_bytes
):
    """
    Verify a photo classified as "dog" is saved to disk and recorded in the
    database as accepted.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    upload_dir : pathlib.Path
        Temp directory `UPLOAD_FOLDER` is redirected to for this test.
    force_inference : Callable[[str, float], None]
        Fixture used to force the classifier to return a fixed label and
        confidence.
    sample_image_bytes : bytes
        Bytes of a real image to upload.
    """
    force_inference("dog", 0.95)
    original_filename = f"{uuid.uuid4()}.jpg"

    response = client.post(
        "/upload",
        files=[
            ("files", (original_filename, sample_image_bytes, "image/jpeg"))
        ],
    )

    assert response.status_code == 200
    assert "uploaded successfully" in response.text

    row = _fetch_prediction(original_filename)
    assert row is not None
    photo_id, predicted_label = row
    assert predicted_label == "dog"
    assert photo_id is not None

    stored_filename = _fetch_photo_stored_filename(photo_id)
    assert stored_filename is not None
    saved_file = upload_dir / stored_filename
    assert saved_file.read_bytes() == sample_image_bytes


def test_upload_rejects_non_dog_photo(
    client, 
    upload_dir, 
    force_inference, 
    sample_image_bytes
):
    """
    Verify a photo classified as something other than "dog" is rejected,
    recorded as not accepted with no photo id, and never written to disk.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    upload_dir : pathlib.Path
        Temp directory `UPLOAD_FOLDER` is redirected to for this test.
    force_inference : Callable[[str, float], None]
        Fixture used to force the classifier to return a fixed label and
        confidence.
    sample_image_bytes : bytes
        Bytes of a real image to upload.
    """
    force_inference("cat", 0.80)
    original_filename = f"{uuid.uuid4()}.jpg"

    response = client.post(
        "/upload",
        files=[
            ("files", (original_filename, sample_image_bytes, "image/jpeg"))
        ],
    )

    assert response.status_code == 200
    assert 'class="message error"' in response.text

    row = _fetch_prediction(original_filename)
    assert row is not None
    photo_id, predicted_label = row
    assert predicted_label == "cat"
    assert photo_id is None

    assert list(upload_dir.iterdir()) == []


def test_upload_rejects_disallowed_extension(client, upload_dir, monkeypatch):
    """
    Verify a file with a disallowed extension is rejected before
    classification ever runs, and nothing is written to disk.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    upload_dir : pathlib.Path
        Temp directory `UPLOAD_FOLDER` is redirected to for this test.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to replace `src.app.inference` with a
        mock so the test can assert it was never called.
    """
    mock_inference = MagicMock()
    monkeypatch.setattr("src.app.inference", mock_inference)

    response = client.post(
        "/upload",
        files=[("files", ("note.txt", b"not an image", "text/plain"))],
    )

    assert response.status_code == 200
    assert 'class="message error"' in response.text
    mock_inference.assert_not_called()
    assert list(upload_dir.iterdir()) == []


def test_upload_partial_success(client, force_inference, sample_image_bytes):
    """
    Verify a mixed batch upload (one valid image, one disallowed file)
    reports a partial success with correct accept/reject counts.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    force_inference : Callable[[str, float], None]
        Fixture used to force the classifier to return a fixed label and
        confidence.
    sample_image_bytes : bytes
        Bytes of a real image to upload.
    """
    force_inference("dog", 0.95)
    good_filename = f"{uuid.uuid4()}.jpg"

    response = client.post(
        "/upload",
        files=[
            ("files", (good_filename, sample_image_bytes, "image/jpeg")),
            ("files", ("note.txt", b"not an image", "text/plain")),
        ],
    )

    assert response.status_code == 200
    assert 'class="message partial"' in response.text
    assert "Accepted 1" in response.text
    assert "rejected 1" in response.text


def test_upload_rejected_when_shutting_down(
    client, 
    upload_dir, 
    monkeypatch, 
    sample_image_bytes
):
    """
    Verify uploads are rejected with a 503 while the app is shutting down,
    and nothing is written to disk.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    upload_dir : pathlib.Path
        Temp directory `UPLOAD_FOLDER` is redirected to for this test.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to flip `client.app.state.shutting_down`.
    sample_image_bytes : bytes
        Bytes of a real image to upload.
    """
    monkeypatch.setattr(client.app.state, "shutting_down", True)

    response = client.post(
        "/upload",
        files=[
            ("files", (f"{uuid.uuid4()}.jpg", sample_image_bytes, "image/jpeg"))
        ],
    )

    assert response.status_code == 503
    assert list(upload_dir.iterdir()) == []


def test_view_photos_lists_only_allowed_extensions(client, monkeypatch):
    """
    Verify the gallery page lists only files with allowed extensions.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to stub `os.listdir` with a fixed
        directory manifest.
    """
    monkeypatch.setattr("os.listdir", lambda _: ["a.jpg", "b.txt", "c.png"])

    response = client.get("/photos")

    assert response.status_code == 200
    assert "/photos/a.jpg" in response.text
    assert "/photos/c.png" in response.text
    assert "/photos/b.txt" not in response.text


def test_serve_photo_returns_file(client, tmp_path, monkeypatch):
    """
    Verify a photo is served from disk with the expected caching header.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        Test client fixture for hitting the real app routes.
    tmp_path : pathlib.Path
        Built-in pytest fixture providing a per-test temp directory, used
        here as the redirected `UPLOAD_FOLDER`.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to redirect `src.app.UPLOAD_FOLDER`.
    """
    monkeypatch.setattr("src.app.UPLOAD_FOLDER", str(tmp_path))
    contents = b"fake-image-bytes"
    (tmp_path / "photo.jpg").write_bytes(contents)

    response = client.get("/photos/photo.jpg")

    assert response.status_code == 200
    assert response.content == contents
    assert response.headers[
        "cache-control"
    ] == "public, max-age=31536000, immutable"
