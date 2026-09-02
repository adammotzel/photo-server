# App Testing

App testing setup documentation.

## Setup

Create the test database, user, tables, and grants by running
[scripts/db/create_test_db.sql](../../scripts/db/create_test_db.sql) as a Postgres admin user:

```bash
psql -U <admin_user> -f scripts/db/create_test_db.sql
```

The script prompts for the `photoapp_user_test` password. Store the value you enter in the `.env.test` file as `DB_PASSWORD`. 

It then creates the `photoapp_user` role, the `photoapp` database, tables, and grants. It's safe to re-run.

## Unit Testing

Unit tests use [pytest](https://docs.pytest.org/), with coverage reported by `pytest-cov`. 

Both are configured in `pyproject.toml`: `testpaths` points at `tests/`, load tests are excluded (see [Load Testing](#load-testing)), and `addopts` enables a coverage report on every run. Running `pytest` from project root picks all of this up automatically.

### Directory Structure

| Test module | Exercises |
|---|---|
| `tests/app/test_app.py` | `src/app.py` (FastAPI routes) |
| `tests/db/test_db.py` | `src/db.py` (database writes) |
| `tests/model/test_model.py` | `src/model.py` (classifier inference) |
| `tests/utils/test_utils.py` | `src/utils.py` (photo save/cleanup and thumbnail helpers) |

This keeps each suite scoped to a single area of responsibility and makes it
obvious where a new test belongs when a `src/` module changes.

### Fixtures and `conftest.py`

Fixtures are split by scope:

- **`tests/conftest.py`** (root) holds fixtures shared by every suite:
  `sample_image_bytes` (a real image loaded once per session), `IP` (a
  constant local IP address), and `db_pool` (opens the real
  `psycopg_pool.ConnectionPool` from `src.db` once for the whole session and
  closes it at the end). It also loads `.env`, then loads `.env.test` on top
  with `override=True` (so `DB_NAME` / `DB_USER` / `DB_PASSWORD` resolve to
  the test database) before any `src.*` module is imported, since
  `src/constants.py` builds `Config()` at import time.
- **`tests/app/conftest.py`** holds fixtures specific to the app suite: a
  `client` fixture wrapping `TestClient` around the real FastAPI app (with
  the app's own pool open/close calls patched to no-ops, since `db_pool`
  already owns that lifecycle), an autouse `upload_dir` fixture that
  redirects `UPLOAD_FOLDER` to a temp directory for every test in the module,
  and a `force_inference` helper for stubbing the classifier's output
  deterministically.

Suites that need the database (`test_app.py`, `test_db.py`) pull in
`db_pool` at the module level via `pytestmark = pytest.mark.usefixtures("db_pool")`,
so every test in the module runs against a live connection pool without
each test having to request it by name.

### Design Notes

- Tests hit a real, running app and a real Postgres database (`photoapp_test`). Nothing is mocked at the HTTP or SQL layer. Only external effects that would be slow, non-deterministic, or destructive (classifier inference, disk writes) are stubbed or redirected.
- No test ever writes to the real `photos` upload folder; `upload_dir` in `tests/app/conftest.py` redirects every app test to a temp directory that's removed afterward.
- Full docstrings on each test function describe the specific scenario and assertions.

### Cleanup

Periodic cleanup of the test database is necessary because some tests write to the database. Clearing records or reseting the entire db are both valid options.

## Load Testing

Load tests are defined in [tests/load_tests](../../tests/load_tests/). 

### Run Load Tests

Start the app:
```bash
bash scripts/tests/run_test_app.sh
```

The script exports `.env`, then exports `.env.test` on top of it, so `DB_NAME` / `DB_USER` / `DB_PASSWORD` resolve to the test database (same `.env.test` file used by the unit tests, see [02_CONFIG.md](02_CONFIG.md)) instead of production. It has to export `.env` itself because nothing loads it at runtime; this is the same order `tests/conftest.py` uses.

Run the tests:
```bash
bash scripts/tests/run_load_tests.sh
```

The app and load tests are run on separate servers/devices.

Follow [Locust's documentation](https://docs.locust.io/en/stable/quickstart.html) to create more load tests.
