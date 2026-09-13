# App Testing

## Test Database

Create the test database, user, tables, and grants by running
[scripts/db/create_test_db.sql](../../scripts/db/create_test_db.sql) as a Postgres admin user:

```bash
psql -U <admin_user> -f scripts/db/create_test_db.sql
```

The script prompts for the `photoapp_user_test` password. Set `DB_USER`, `DB_NAME`, and `DB_PASSWORD` in `.env.test` to the test values (see [02_CONFIG.md](02_CONFIG.md)).

It creates the `photoapp_user_test` role, the `photoapp_test` database, the tables, and the user's grants. It's safe to re-run.

## Unit Tests

Tests use [pytest](https://docs.pytest.org/) with coverage from `pytest-cov`. Run `pytest` from the project root.

### Layout

One test suite per `src/` module:

| Test module | Exercises |
|---|---|
| `tests/app/test_app.py` | `src/app.py` (FastAPI routes) |
| `tests/db/test_db.py` | `src/db.py` (database writes) |
| `tests/model/test_model.py` | `src/model.py` (classifier inference) |
| `tests/utils/test_utils.py` | `src/utils.py` (photo save/cleanup, thumbnails) |

### Fixtures

- **`tests/conftest.py`** - session fixtures shared by every suite: `sample_image_bytes` and `db_pool` (opens the `psycopg_pool.ConnectionPool` from `src.db` once, closes it at the end). It also loads `.env`, then `.env.test` with `override=True`, before any `src.*` import, since `src/config.py` builds `Config()` at import time.
- **`tests/app/conftest.py`** - app-suite fixtures: `client` (`TestClient` around the real app, with the app's own pool open/close patched to no-ops), autouse `upload_dir` (redirects `UPLOAD_FOLDER` to a temp dir per test), autouse `stub_description` (stubs the OpenAI description call), and `force_inference` (stubs the classifier output). `test_app.py` and `test_db.py` pull in `db_pool` at module level via `pytestmark = pytest.mark.usefixtures("db_pool")`.

### Notes

- Tests run against a real app and a real Postgres database (`photoapp_test`). Nothing is mocked at the HTTP or SQL layer; only slow, non-deterministic, or destructive effects (classifier inference, OpenAI calls, disk writes) are stubbed or redirected.
- No test writes to the real upload folder — `upload_dir` sends every app test to a temp dir.
- Each test function has a brief docstring describing its purpose.
- The test database needs periodic cleanup (clear records or reseed) since tests write to it.
