-- Clears out all test dabase tables, except for alembic

DO $$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
          AND tablename != 'alembic_version'
    ) LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE;';
    END LOOP;
END $$;
