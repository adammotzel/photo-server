import os
from pathlib import Path

from dotenv import load_dotenv

# must run before any `src.*` module is imported,
# since src/config.py builds Config() at import time
_ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT_DIR / ".env")

# forces test database usage
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
    """
    from src.database.transactions import engine

    try:
        yield engine
    finally:
        engine.dispose()
