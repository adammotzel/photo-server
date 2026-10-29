#!/usr/bin/env bash

echo "Reading environment variables..."

set -a
source .env
source .env.test
set +a

if [[ "$DB_NAME" == *"test"* ]]; then
    echo "Environment variables loaded."
else
    echo "Must run tests using the test database. Received $DB_NAME."
    exit 1
fi

echo "Running unit tests..."

uv run pytest

echo "Clearing $DB_NAME..."

# clear test records from database
PGPASSWORD="$DB_PGSQL_PW" psql \
    -h "$DB_HOST" \
    -U postgres \
    -d "$DB_NAME" \
    -f $(pwd)/scripts/database/_clear_test_db.sql \

echo "Database $DB_NAME cleared. Tests complete."
