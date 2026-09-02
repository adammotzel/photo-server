#!/bin/bash

# nothing loads .env at runtime, so export it here, then let .env.test
# override DB_NAME/DB_USER/DB_PASSWORD with the test database's credentials
# (same order as tests/conftest.py)
set -a
source .env
source .env.test
set +a

uv run python -m scripts.run
