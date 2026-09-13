import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.db import pool
from src.types import Description

DEFAULT_DESCRIPTION = "A very good dog, allegedly."


@pytest.fixture(scope="module")
def client():
    """
    A `TestClient` wired to the real FastAPI app and `photoapp_test` database.

    `lifespan()`'s `pool.open()`/`pool.close()` calls are neutralized: the
    pool can't be reopened once closed, and it is also used by the `db` suite,
    so only the session-wide `db_pool` fixture may close it.
    """
    mp = pytest.MonkeyPatch()
    mp.setattr(pool, "open", lambda *args, **kwargs: None)
    mp.setattr(pool, "close", lambda *args, **kwargs: None)

    with TestClient(app) as test_client:
        yield test_client

    mp.undo()


@pytest.fixture(autouse=True)
def upload_dir(monkeypatch):
    """
    Redirect `UPLOAD_FOLDER` to a temp dir, so no test can touch the real
    `photos` folder.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setattr("src.app.UPLOAD_FOLDER", tmp_dir)
        yield Path(tmp_dir)


@pytest.fixture(autouse=True)
def stub_description(monkeypatch):
    """
    Stub `src.app.describe_image` so no test calls the OpenAI API.

    Returns a helper that re-stubs it with a specific description.
    """

    def _force(description: str = DEFAULT_DESCRIPTION) -> None:
        result = Description(description, 100, 20, "test-model")
        monkeypatch.setattr("src.app.describe_image", lambda contents: result)

    _force()

    return _force


@pytest.fixture
def force_inference(monkeypatch):
    """
    Return a helper that makes `src.app.inference` return a fixed
    `(label, confidence)` pair.
    """

    def _force(label: str, confidence: float) -> None:
        monkeypatch.setattr(
            "src.app.inference", lambda processor, model, contents: (label, confidence)
        )

    return _force
