# PostgreSQL Database Setup

Run [scripts/db/create_db.sql](../../scripts/db/create_db.sql) as a Postgres admin user from a `psql` shell:

```bash
psql -U <admin_user> -f scripts/db/create_db.sql
```

The script prompts for the `photoapp_user` password. Put that value in `.env` as `DB_PASSWORD`.

It creates the `photoapp_user` role, the `photoapp` database, the tables (`photos`, `networks`, `predictions`), and the app user's grants. It's safe to re-run.

See [DATABASE.md](../architecture/DATABASE.md) for schemas and design notes.
