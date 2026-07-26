import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.db import pool


@pytest.fixture(scope="module")
def client():
    """
    Build a `TestClient` wired to the real FastAPI app.

    `test_app.py`'s `pytestmark` pulls in the session-wide `db_pool` fixture
    (see root conftest.py), which is already open by the time this runs, so
    upload tests write real rows to `photoapp_test`. `lifespan()`'s own
    `pool.open()`/`pool.close()` calls are neutralized here; `ConnectionPool`
    can't be reopened once closed, and this pool is a session-wide feature
    also used by the `db` test suite, so only `db_pool` may actually close it.

    Yields
    ------
    fastapi.testclient.TestClient
        A client hitting the real app routes, with its `lifespan` pool
        open/close calls patched to no-ops.
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
    Redirect `UPLOAD_FOLDER` to a temp dir that is always removed afterward.

    Autouse so no test in this module can accidentally upload to or delete
    from the real `src/photos` folder, even if it doesn't request this
    fixture by name.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to patch `src.app.UPLOAD_FOLDER` for the
        duration of the test.

    Yields
    ------
    pathlib.Path
        Path to the temporary upload directory.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setattr("src.app.UPLOAD_FOLDER", tmp_dir)
        yield Path(tmp_dir)


@pytest.fixture
def force_inference(monkeypatch):
    """
    Provide a helper to make `src.app.inference` deterministic.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Built-in pytest fixture used to patch `src.app.inference`.

    Returns
    -------
    Callable[[str, float], None]
        A function that, when called with a label and confidence, patches
        `src.app.inference` to always return that `(label, confidence)` pair.
    """

    def _force(label: str, confidence: float) -> None:
        """
        Patch `src.app.inference` to return a fixed label and confidence.

        Parameters
        ----------
        label : str
            Predicted class label `inference` should return.
        confidence : float
            Confidence score `inference` should return.

        Returns
        -------
        None
        """
        monkeypatch.setattr("src.app.inference", lambda contents: (label, confidence))

    return _force
