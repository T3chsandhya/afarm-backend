-- AFARM only — does not modify other databases on this Postgres instance.
-- Replace CHANGE_ME before running.

CREATE USER afarm_app WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';

CREATE DATABASE afarm
  OWNER afarm_app
  ENCODING 'UTF8'
  TEMPLATE template0;

\c afarm

GRANT ALL ON SCHEMA public TO afarm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO afarm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO afarm_app;