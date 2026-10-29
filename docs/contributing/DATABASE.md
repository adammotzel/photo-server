# Contributing: Database

Guidelines for database changes.

## Migrations

Generate a new alembic migration:

```bash
alembic revision --autogenerate -m "migration description goes here"
```

Preview the migration:

```bash
alembic upgrade head --sql
```

Run the migrations via the migration script (handles both databases):

```bash
./scripts/database/run_migrations.sh
```
