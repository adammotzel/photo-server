-- Safe to re-run

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'db_user')
\gexec

SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE photos TO %I', :'db_user')
\gexec

SELECT format('GRANT USAGE, SELECT, UPDATE ON SEQUENCE photos_id_seq TO %I', :'db_user')
\gexec

SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE networks TO %I', :'db_user')
\gexec

SELECT format('GRANT USAGE, SELECT, UPDATE ON SEQUENCE networks_id_seq TO %I', :'db_user')
\gexec

SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE predictions TO %I', :'db_user')
\gexec

SELECT format('GRANT USAGE, SELECT, UPDATE ON SEQUENCE predictions_id_seq TO %I', :'db_user')
\gexec

SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE descriptions TO %I', :'db_user')
\gexec

SELECT format('GRANT USAGE, SELECT, UPDATE ON SEQUENCE descriptions_id_seq TO %I', :'db_user')
\gexec
