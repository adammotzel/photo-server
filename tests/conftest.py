import os
from pathlib import Path

from dotenv import load_dotenv

# must run before any `src.*` module is imported anywhere during collection,
# since src/constants.py builds Config() (and src/db.py its pool) at import time
_ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_ROOT_DIR / ".env.test", override=True)

import pytest

IMG_DIR = _ROOT_DIR / "data" / "training"

# last line of defense!
if "test" not in os.environ["DB_NAME"].lower():
    raise RuntimeError("Tests must be executed using the test database.")


@pytest.fixture(scope="session")
def sample_image_bytes() -> bytes:
    """
    Load the raw bytes of a real image.

    Session-scoped since the file is read once and the bytes are immutable;
    any test that just needs *some* valid image can share the same object.

    Returns
    -------
    bytes
        Raw bytes of the first `.jpg` / `.jpeg` / `.png` file found in
        `IMG_DIR`.
    """

    image_path = next(
        p for p in sorted(IMG_DIR.iterdir())
        if p.suffix in (".jpg", ".jpeg", ".png")
    )

    return image_path.read_bytes()


@pytest.fixture(scope="session")
def IP() -> str:
    """
    Provide a constant address for tests that need an uploader IP.

    Returns
    -------
    str
        The literal string `"127.0.0.1"`.
    """
    return "127.0.0.1"


@pytest.fixture(scope="session")
def db_pool():
    """
    Open the real `photoapp_test` connection pool exactly once for the whole
    session.

    `psycopg_pool.ConnectionPool` cannot be reopened once closed, and it's shared 
    by every test that imports `src.db` (or `src.app`), so only one place may own 
    its open/close lifecycle.

    Yields
    ------
    psycopg_pool.ConnectionPool
        The open, session-wide connection pool defined in `src.db`.
    """
    from src.db import pool

    pool.open()
    yield pool
    pool.close()
