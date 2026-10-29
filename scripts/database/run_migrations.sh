#!/bin/bash

DB_TO_MIGRATE="photoapp" alembic upgrade head

echo "photoapp migration complete"

DB_TO_MIGRATE="photoapp_test" alembic upgrade head

echo "photoapp_test migration complete"
