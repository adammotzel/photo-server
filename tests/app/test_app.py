import re
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import PHOTO_CACHE_HEADERS, config
from src.db import pool, write_description, write_photo_metadata
from src.types import Description
from src.utils import thumbnail_path, write_thumbnail

pytestmark = pytest.mark.usefixtures("db_pool")


def _upload(client, *files: tuple[str, bytes, str]):
    """
    POST `(filename, contents, content_type)` tuples to `/upload`.
    """
    return client.post("/upload", files=[("files", file) for file in files])


def _fetch_prediction(original_filename: str) -> tuple[int | None, str] | None:
    """
    Return `(photo_id, predicted_label)` for an upload, or `None` if no
    prediction was recorded.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id, predicted_label "
                "FROM predictions WHERE original_filename = %s",
                (original_filename,),
            )
            return cur.fetchone()


def _fetch_photo(photo_id: int) -> tuple[str, str | None]:
    """
    Return `(stored_filename, description)` for a `photos` row.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.stored_filename, d.description "
                "FROM photos p "
                "LEFT JOIN descriptions d ON d.id = p.description_id "
                "WHERE p.id = %s",
                (photo_id,),
            )
            row = cur.fetchone()
            assert row is not None, f"no photos row with id {photo_id}"
            return row


def _write_photo(description: str | None = None) -> str:
    """
    Insert a `photos` row, optionally with a linked description, and return
    its stored filename.
    """
    stored_filename = f"{uuid.uuid4()}.jpg"
    photo_id = write_photo_metadata(stored_filename, "image/jpeg")

    if description is not None:
        write_description(photo_id, description, 100, 20, "test-model")

    return stored_filename


def test_read_root(client):
    """
    Verify the home page loads and displays the configured app name.
    """
    response = client.get("/")

    assert response.status_code == 200
    assert config.name in response.text


def test_upload_form_renders_without_results(client):
    """
    Verify the upload form loads with no result sections before an upload.
    """
    response = client.get("/upload")

    assert response.status_code == 200
    assert "/thumbnails/" not in response.text
    assert "Accepted (" not in response.text
    assert "Rejected (" not in response.text


def test_upload_saves_accepted_dog_photo(
    client,
    upload_dir,
    force_inference,
    stub_description,
    sample_image_bytes,
):
    """
    Verify a photo classified as a dog is recorded as a prediction, saved to
    disk with a thumbnail, and linked to its description.
    """
    force_inference("dog", 0.95)
    description = f"Description {uuid.uuid4()}"
    stub_description(description)
    original_filename = f"{uuid.uuid4()}.jpg"

    response = _upload(client, (original_filename, sample_image_bytes, "image/jpeg"))

    assert response.status_code == 200
    assert "uploaded successfully" in response.text

    row = _fetch_prediction(original_filename)
    assert row is not None
    photo_id, predicted_label = row
    assert predicted_label == "dog"

    stored_filename, stored_description = _fetch_photo(photo_id)
    assert stored_description == description
    assert (upload_dir / stored_filename).read_bytes() == sample_image_bytes
    assert Path(thumbnail_path(str(upload_dir), stored_filename)).exists()


def test_upload_lists_accepted_photo_with_thumbnail(
    client,
    force_inference,
    sample_image_bytes,
):
    """
    Verify an accepted upload is listed by its original filename, with a
    thumbnail served from its stored filename.
    """
    force_inference("dog", 0.95)
    original_filename = f"{uuid.uuid4()}.jpg"

    response = _upload(client, (original_filename, sample_image_bytes, "image/jpeg"))

    row = _fetch_prediction(original_filename)
    assert row is not None
    stored_filename, _ = _fetch_photo(row[0])

    # the uploader sees the name they recognize, not the stored uuid
    assert original_filename in response.text
    assert f'src="/thumbnails/{stored_filename}"' in response.text


def test_upload_rejects_non_dog_photo(
    client,
    upload_dir,
    force_inference,
    sample_image_bytes,
):
    """
    Verify a non-dog photo is reported with a reason, recorded as a prediction
    with no photo, and never written to disk.
    """
    force_inference("cat", 0.80)
    original_filename = f"{uuid.uuid4()}.jpg"

    response = _upload(client, (original_filename, sample_image_bytes, "image/jpeg"))

    assert response.status_code == 200
    assert 'class="message error"' in response.text
    assert original_filename in response.text
    assert "not a dog (cat, 80%)" in response.text
    assert "/thumbnails/" not in response.text

    assert _fetch_prediction(original_filename) == (None, "cat")
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("note.txt", "text/plain"),
        ("note.txt", "image/jpeg"),
        ("photo.jpg", "text/plain"),
    ],
    ids=["both-wrong", "bad-extension", "bad-mime-type"],
)
def test_upload_rejects_unsupported_file_type(
    client,
    upload_dir,
    monkeypatch,
    filename,
    content_type,
):
    """
    Verify a file is rejected before classification unless both its extension
    and MIME type are allowed.
    """
    mock_inference = MagicMock()
    monkeypatch.setattr("src.app.inference", mock_inference)

    response = _upload(client, (filename, b"not an image", content_type))

    assert response.status_code == 200
    assert 'class="message error"' in response.text
    assert "unsupported file type" in response.text
    mock_inference.assert_not_called()
    assert list(upload_dir.iterdir()) == []


def test_upload_reports_partial_success(client, force_inference, sample_image_bytes):
    """
    Verify a mixed batch reports accept/reject counts and lists both outcomes,
    accepted first, with a thumbnail for the accepted file only.
    """
    force_inference("dog", 0.95)
    good_filename = f"{uuid.uuid4()}.jpg"

    response = _upload(
        client,
        (good_filename, sample_image_bytes, "image/jpeg"),
        ("note.txt", b"not an image", "text/plain"),
    )

    assert response.status_code == 200
    assert 'class="message partial"' in response.text
    assert "Accepted 1 image(s), rejected 1 image(s)." in response.text
    assert "Accepted (1)" in response.text
    assert "Rejected (1)" in response.text
    assert response.text.count('src="/thumbnails/') == 1
    assert response.text.index(good_filename) < response.text.index("note.txt")


def test_upload_survives_description_failure(
    client,
    force_inference,
    sample_image_bytes,
    monkeypatch,
):
    """
    Verify a dog photo is still accepted and saved, without a description,
    when the description call fails.
    """
    force_inference("dog", 0.95)

    def _boom(contents):
        raise RuntimeError("the LLM is having a day")

    monkeypatch.setattr("src.app.describe_image", _boom)
    original_filename = f"{uuid.uuid4()}.jpg"

    response = _upload(client, (original_filename, sample_image_bytes, "image/jpeg"))

    assert response.status_code == 200
    assert "uploaded successfully" in response.text

    row = _fetch_prediction(original_filename)
    assert row is not None
    photo_id, _ = row
    assert photo_id is not None
    assert _fetch_photo(photo_id)[1] is None


def test_upload_describes_photo_after_saving_it(
    client,
    force_inference,
    sample_image_bytes,
    monkeypatch,
):
    """
    Verify the description is written in the background: by the time the LLM
    is called, the photo and its prediction are already saved without one.
    """
    force_inference("dog", 0.95)
    original_filename = f"{uuid.uuid4()}.jpg"
    description = f"Description {uuid.uuid4()}"
    seen_at_describe_time = []

    def _describe(contents):
        row = _fetch_prediction(original_filename)
        seen_at_describe_time.append((row, _fetch_photo(row[0])[1] if row else None))
        return Description(description, 100, 20, "test-model")

    monkeypatch.setattr("src.app.describe_image", _describe)

    response = _upload(client, (original_filename, sample_image_bytes, "image/jpeg"))

    assert response.status_code == 200
    assert "uploaded successfully" in response.text

    [(row, description_then)] = seen_at_describe_time
    assert row is not None
    assert description_then is None

    assert _fetch_photo(row[0])[1] == description


def test_upload_escapes_client_supplied_filenames(client):
    """
    Verify a client-supplied filename containing markup is escaped rather than
    rendered into the page.
    """
    response = _upload(client, ("<script>alert(1)</script>.txt", b"nope", "text/plain"))

    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_upload_rejected_when_shutting_down(
    client,
    upload_dir,
    monkeypatch,
    sample_image_bytes,
):
    """
    Verify uploads are refused with a 503 while the app is shutting down.
    """
    monkeypatch.setattr(client.app.state, "shutting_down", True)

    response = _upload(client, (f"{uuid.uuid4()}.jpg", sample_image_bytes, "image/jpeg"))

    assert response.status_code == 503
    assert list(upload_dir.iterdir()) == []


def test_view_photos_orders_newest_first(client):
    """
    Verify the gallery lists photos newest-upload-first.
    """
    older = _write_photo()
    newer = _write_photo()

    response = client.get("/photos")

    assert response.status_code == 200
    assert response.text.index(newer) < response.text.index(older)


def test_view_photos_pagination(client, monkeypatch):
    """
    Verify photos overflow onto the next page once a page fills up.
    """
    # shrink the page so the test doesn't depend on existing rows in the db
    monkeypatch.setattr("src.app.PHOTOS_PAGE_SIZE", 2)

    oldest, *newest_two = [_write_photo() for _ in range(3)]

    page_one = client.get("/photos")
    assert page_one.status_code == 200
    assert all(name in page_one.text for name in newest_two)
    assert oldest not in page_one.text
    assert "?page=2" in page_one.text

    page_two = client.get("/photos", params={"page": 2})
    assert page_two.status_code == 200
    assert oldest in page_two.text


def test_gallery_links_thumbnails_to_full_size_photos(client):
    """
    Verify the gallery grid renders thumbnails, not originals, each linking to
    its full-size photo.
    """
    filename = _write_photo()

    response = client.get("/photos")

    assert response.status_code == 200
    assert f'src="/thumbnails/{filename}"' in response.text
    assert f'href="/photos/{filename}"' in response.text
    assert f'src="/photos/{filename}"' not in response.text


def test_gallery_puts_description_in_data_attribute(client):
    """
    Verify each tile carries its description as data for the lightbox, rather
    than rendering it into the grid.
    """
    description = f"Description {uuid.uuid4()}"
    filename = _write_photo(description)

    response = client.get("/photos")

    assert response.status_code == 200
    assert re.search(
        rf'href="/photos/{re.escape(filename)}"[^>]*'
        rf'data-description="{re.escape(description)}"',
        response.text,
    )
    assert f">{description}<" not in response.text


def test_gallery_renders_photo_without_description(client):
    """
    Verify a photo with no description still renders, with an empty data
    attribute.
    """
    filename = _write_photo()

    response = client.get("/photos")

    assert response.status_code == 200
    assert re.search(
        rf'href="/photos/{re.escape(filename)}"[^>]*data-description=""',
        response.text,
    )


def test_gallery_escapes_descriptions(client):
    """
    Verify a description containing markup is escaped rather than breaking out
    of its data attribute.
    """
    _write_photo('"><script>alert(1)</script>')

    response = client.get("/photos")

    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_serve_thumbnail_returns_thumbnail(client, upload_dir, sample_image_bytes):
    """
    Verify the thumbnail route serves the WebP thumbnail, not the original,
    with long-lived caching.
    """
    stored_filename = f"{uuid.uuid4()}.jpg"
    (upload_dir / stored_filename).write_bytes(sample_image_bytes)
    write_thumbnail(sample_image_bytes, thumbnail_path(str(upload_dir), stored_filename))

    response = client.get(f"/thumbnails/{stored_filename}")

    assert response.status_code == 200
    assert len(response.content) < len(sample_image_bytes)
    assert response.headers["cache-control"] == PHOTO_CACHE_HEADERS["Cache-Control"]

    # not guessed from the extension: '.webp' is missing from some platforms'
    # mimetype registries, and octet-stream makes browsers download the tile
    assert response.headers["content-type"] == "image/webp"


def test_serve_thumbnail_falls_back_to_original(client, upload_dir, sample_image_bytes):
    """
    Verify a photo with no thumbnail on disk is served as the original instead.
    """
    stored_filename = f"{uuid.uuid4()}.jpg"
    (upload_dir / stored_filename).write_bytes(sample_image_bytes)

    response = client.get(f"/thumbnails/{stored_filename}")

    assert response.status_code == 200
    assert response.content == sample_image_bytes


def test_serve_photo_returns_file(client, upload_dir):
    """
    Verify a full-size photo is served from disk with long-lived caching.
    """
    contents = b"fake-image-bytes"
    (upload_dir / "photo.jpg").write_bytes(contents)

    response = client.get("/photos/photo.jpg")

    assert response.status_code == 200
    assert response.content == contents
    assert response.headers["cache-control"] == PHOTO_CACHE_HEADERS["Cache-Control"]
