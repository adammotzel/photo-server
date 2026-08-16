# PostgreSQL Database Setup

App database setup documentation. Run [scripts/db/create_db.sql](../../scripts/db/create_db.sql)
as a Postgres admin user from a `psql` shell:

```bash
psql -U <admin_user> -f scripts/db/create_db.sql
```

The script prompts for the `photoapp_user` password. Store the value you enter in the `.env` file as `DB_PASSWORD`. 

It then creates the `photoapp_user` role, the `photoapp` database, tables, and grants. It's safe to re-run.

## Tables

- `photos`
- `networks`
- `predictions`

See [DATABASE.md](../architecture/DATABASE.md) for schemas and design notes.

## Grants

The app user gets `SELECT, INSERT, UPDATE, DELETE`, and `USAGE, SELECT, UPDATE` on the database tables.
