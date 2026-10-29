#!/usr/bin/env bash

set -a
source .env
source .env.test
set +a

# create the test database if it does not exist
PGPASSWORD="$DB_PGSQL_PW" psql \
    -h "$DB_HOST" \
    -U postgres \
    -d postgres \
    -f $(pwd)/scripts/database/_create_test_db.sql \
    -v db_name="$DB_NAME"

export TEST_DATABASE_URL="postgresql://postgres:$DB_PGSQL_PW@$DB_HOST/$DB_NAME"

# run migrations
ALEMBIC_DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head

# apply grants
PGPASSWORD="$DB_PGSQL_PW" psql \
    -h "$DB_HOST" \
    -U postgres \
    -d "$DB_NAME" \
    -f $(pwd)/scripts/database/_apply_grants.sql \
    -v db_user="$DB_USER" \
    -v db_name="$DB_NAME"

echo "Test database is ready."
