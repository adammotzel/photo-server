-- Safe to re-run

-- create database if missing
SELECT format('CREATE DATABASE %I', :'db_name')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name')
\gexec
