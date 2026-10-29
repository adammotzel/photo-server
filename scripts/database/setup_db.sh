#!/usr/bin/env bash

# load env variables from .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "Unable to load environment variables: no .env file found"
fi

# create photoapp database and app role if they does not exist
PGPASSWORD="$DB_PGSQL_PW" psql \
    -h "$DB_HOST" \
    -U postgres \
    -d postgres \
    -f $(pwd)/scripts/database/_create_db.sql \
    -v db_user="$DB_USER" \
    -v db_password="$DB_PASSWORD" \
    -v db_name="$DB_NAME"

# run migrations
alembic upgrade head

# apply grants
PGPASSWORD="$DB_PGSQL_PW" psql \
    -h "$DB_HOST" \
    -U postgres \
    -d "$DB_NAME" \
    -f $(pwd)/scripts/database/_apply_grants.sql \
    -v db_user="$DB_USER" \
    -v db_name="$DB_NAME"
    