import os
from pathlib import Path

from dotenv import load_dotenv

# must run before any `src.*` module is imported anywhere during collection,
# since src/config.py builds Config() (and src/db.py its pool) at import time
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
    Raw bytes of the first real image in `IMG_DIR`, read once per session.
    """
    image_path = next(
        p for p in sorted(IMG_DIR.iterdir())
        if p.suffix in (".jpg", ".jpeg", ".png")
    )

    return image_path.read_bytes()


@pytest.fixture(scope="session")
def db_pool():
    """
    Open the `photoapp_test` connection pool exactly once for the session.

    `psycopg_pool.ConnectionPool` cannot be reopened once closed, and it's
    shared by every test that imports `src.db` (or `src.app`), so only this
    fixture may own its open/close lifecycle.
    """
    from src.db import pool

    pool.open()
    yield pool
    pool.close()
