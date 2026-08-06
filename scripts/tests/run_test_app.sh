#!/bin/bash

# override DB_NAME/DB_USER/DB_PASSWORD with the test database's credentials
# before scripts.run loads .env (load_dotenv doesn't clobber already-set vars)
set -a
source .env.test
set +a

uv run python -m scripts.run
