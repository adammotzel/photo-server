# PostgreSQL Database Setup

App database setup documentation. All steps must be completed using your Postgres admin user and the `psql` shell.

If you don't have Postgres, download it [here](https://www.postgresql.org/download/).

## Initial App Setup

#### Create app user:
```sql
CREATE USER photoapp_user WITH PASSWORD "secret-goes-here";
```

Store the secret in the `src/.env` file with the name `POSTGRES_PW`.

#### Create new db:
```sql
CREATE DATABASE photoapp;
```

Switch to new db:
```sql
\c photoapp
```

#### Grant access to db:
```sql
GRANT CONNECT ON DATABASE photoapp TO photoapp_user;
```

## Tables

### Photos Table

#### Create `photos` table:
```sql
CREATE TABLE photos (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
    stored_filename TEXT NOT NULL UNIQUE, 
    content_type TEXT, 
    uploaded_by TEXT NOT NULL, 
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Grant access to app user:
```sql
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE photos
TO photoapp_user;

GRANT USAGE, SELECT, UPDATE 
ON SEQUENCE photos_id_seq 
TO photoapp_user;
```

### Predictions Table

#### Create `predictions` table:
```sql
CREATE TABLE predictions (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    photo_id INT REFERENCES photos(id) ON DELETE SET NULL,
    original_filename TEXT NOT NULL,
    predicted_label TEXT NOT NULL,
    confidence REAL NOT NULL,
    accepted BOOLEAN NOT NULL,
    uploaded_by TEXT NOT NULL,
    predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

`photo_id` is nullable because rejected uploads (predicted label != "dog") are never saved to 
the `photos` table, but the prediction is still logged for model evaluation. `ON DELETE SET NULL` 
keeps prediction history intact if a photo is later removed.

#### Grant access to app user:
```sql
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE predictions
TO photoapp_user;

GRANT USAGE, SELECT, UPDATE 
ON SEQUENCE predictions_id_seq 
TO photoapp_user;
```

### Users Table

#### Create `users` table:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Grant access to app user:
```sql
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE users
TO photoapp_user;

GRANT USAGE, SELECT, UPDATE 
ON SEQUENCE users_id_seq 
TO photoapp_user;
```
