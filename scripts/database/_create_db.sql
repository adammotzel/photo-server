-- Safe to re-run

-- create app user role if missing
SELECT format('CREATE USER %I WITH PASSWORD %L', :'db_user', :'db_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = :'db_user')
\gexec

-- create database if missing
SELECT format('CREATE DATABASE %I', :'db_name')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name')
\gexec
