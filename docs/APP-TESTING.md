# App Testing

## Test Setup

Create a test database:

```sql
CREATE DATABASE photoapp_test WITH TEMPLATE photoapp;
```

This will create a copy of the true app database, including all data.

Switch to the new database and grant access to the app user:

```sql
GRANT CONNECT ON DATABASE photoapp_test TO photoapp_user;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE photos
TO photoapp_user;

GRANT USAGE, SELECT, UPDATE 
ON SEQUENCE photos_id_seq 
TO photoapp_user;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE predictions
TO photoapp_user;

GRANT USAGE, SELECT, UPDATE 
ON SEQUENCE predictions_id_seq 
TO photoapp_user;
```

## Unit Testing

Unit tests use [pytest](https://docs.pytest.org/), with coverage reported by
`pytest-cov`. Both are configured in `pyproject.toml`: `testpaths` points at
`tests/`, `tests/load_tests` is excluded see [Load Testing](#load-testing), 
and `addopts` enables a `--cov=src --cov-report=term-missing` report on every 
run. Running `pytest` from project root picks all of this up automatically.

### Directory Structure

Test modules under `tests/` mirror the modules they exercise in `src/`:

| Test module | Exercises |
|---|---|
| `tests/app/test_app.py` | `src/app.py` (FastAPI routes) |
| `tests/db/test_db.py` | `src/db.py` (database writes) |
| `tests/model/test_model.py` | `src/model.py` (classifier inference) |
| `tests/utils/test_utils.py` | `src/utils.py` (photo save/cleanup helpers) |

This keeps each suite scoped to a single area of responsibility and makes it
obvious where a new test belongs when a `src/` module changes.

### Fixtures and `conftest.py`

Fixtures are split by scope:

- **`tests/conftest.py`** (root) holds fixtures shared by every suite:
  `sample_image_bytes` (a real image loaded once per session), `IP` (a
  constant local IP address), and `db_pool` (opens the real
  `psycopg_pool.ConnectionPool` from `src.db` once for the whole session and
  closes it at the end). It also sets `ENVIRONMENT=test` before any `src.*`
  module is imported, since `src/config.py` resolves the database name from
  that variable at import time.
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

- Tests hit the real app and a real Postgres database (`photoapp_test`).
  Nothing is mocked at the HTTP or SQL layer. Only external effects that
  would be slow, non-deterministic, or destructive (classifier inference,
  disk writes) are stubbed or redirected.
- No test ever writes to the real `src/photos` upload folder; `upload_dir` in
  `tests/app/conftest.py` redirects every app test to a temp directory that's
  removed automatically afterward.
- Full docstrings on each test function describe the specific scenario and
  assertions.

### Cleanup

I recommend periodically cleaning up the test database because some of the tests 
actually perform write operations.

## Load Testing

Load tests are defined in [tests/load_tests](../tests/load_tests/). 

### Run Load Tests

Start the app:
```bash
bash scripts/tests/run_test_app.sh
```

Run the tests:
```bash
bash scripts/tests/run_load_tests.sh
```

Run the app and load tests on separate servers/devices. You *can* run both on the same device, but results will be skewed because they'll be competing for the same CPU, memory, etc.

Follow [Locust's documentation](https://docs.locust.io/en/stable/quickstart.html) if you want to create more load tests.
