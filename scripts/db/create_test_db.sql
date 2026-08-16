-- Run as a Postgres superuser (or a role with CREATEDB/CREATEROLE) from a
-- psql shell: psql -U <admin_user> -f scripts/db/create_test_db.sql
-- Safe to re-run.

\prompt 'Enter password for photoapp_user_test: ' db_password

-- create role if missing
SELECT format('CREATE USER %I WITH PASSWORD %L', 'photoapp_user_test', :'db_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'photoapp_user_test')
\gexec

-- create database if missing
SELECT format('CREATE DATABASE %I', 'photoapp_test')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'photoapp_test')
\gexec

\c photoapp_test

-- tables

CREATE TABLE IF NOT EXISTS photos (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stored_filename TEXT NOT NULL UNIQUE,
    content_type TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS networks (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS predictions (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    photo_id INT REFERENCES photos(id) ON DELETE SET NULL,
    network_id INT REFERENCES networks(id) ON DELETE SET NULL,
    original_filename TEXT NOT NULL,
    predicted_label TEXT NOT NULL,
    confidence REAL NOT NULL,
    uploader_ip TEXT NOT NULL,
    predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- grants

GRANT CONNECT ON DATABASE photoapp_test TO photoapp_user_test;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE photos
TO photoapp_user_test;

GRANT USAGE, SELECT, UPDATE
ON SEQUENCE photos_id_seq
TO photoapp_user_test;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE predictions
TO photoapp_user_test;

GRANT USAGE, SELECT, UPDATE
ON SEQUENCE predictions_id_seq
TO photoapp_user_test;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE networks
TO photoapp_user_test;

GRANT USAGE, SELECT, UPDATE
ON SEQUENCE networks_id_seq
TO photoapp_user_test;
