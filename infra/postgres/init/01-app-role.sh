#!/bin/sh
# Runs once when the postgres volume is first created.
# Creates the non-owner role the API connects as, so row-level security applies to it.
set -eu

if [ -z "${APP_DB_PASSWORD:-}" ]; then
  echo "APP_DB_PASSWORD is not set" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v app_password="$APP_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE aitms_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aitms_app') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO aitms_app', current_database()) \gexec
CREATE EXTENSION IF NOT EXISTS vector;
SQL
