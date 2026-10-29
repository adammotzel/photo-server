# App Testing

## Test Database

Unit tests utilize the test database. See [02_POSTGRES](02_POSTGRES.md) for instructions.

## Unit Tests

Tests use [pytest](https://docs.pytest.org/) with coverage from `pytest-cov`. Run test using this script:

```bash
./scripts/tests/run_tests.sh
```

This script runs all unit tests then clears the test database (excluding the alembic versions).

### Layout

One test suite per `src/` module:

| Test module | Exercises |
|---|---|
| `tests/app/test_app.py` | `src/app.py` (FastAPI routes) |
| `tests/database/test_transactions.py` | `src/database/transactions.py` (database writes) |
| `tests/model/test_model.py` | `src/model.py` (classifier inference) |
| `tests/utils/test_utils.py` | `src/utils.py` (photo save/cleanup, thumbnails) |

### Fixtures

- **`tests/conftest.py`** - session fixtures shared by every suite: `sample_image_bytes` and `db_pool`. It also loads `.env`, then `.env.test` with `override=True`, before any `src.*` import, since `src/config.py` builds `Config()` at import time.
- **`tests/app/conftest.py`** - app-suite fixtures: `client` (`TestClient` around the real app, with the app's own database engine open/close patched to no-ops), autouse `upload_dir` (redirects `UPLOAD_FOLDER` to a temp dir per test), autouse `stub_description` (stubs the OpenAI description call), and `force_inference` (stubs the classifier output). `test_app.py` and `test_db.py` pull in `db_pool` at module level via `pytestmark = pytest.mark.usefixtures("db_pool")`.

### Notes

- Tests run against a real app and a real Postgres database. Nothing is mocked at the HTTP or SQL layer; only slow, non-deterministic, or destructive effects (classifier inference, OpenAI calls, disk writes) are stubbed or redirected.
- No test writes to the real upload folder; `upload_dir` sends every app test to a temp dir.
- Each test function has a brief docstring describing its purpose.
