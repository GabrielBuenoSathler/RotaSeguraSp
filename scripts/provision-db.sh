#!/bin/sh
# Run inside the db container after migrations, using its administrative identity.
set -eu
if [ "$POSTGRES_APP_USER" = "$POSTGRES_USER" ]; then
  echo "O usuário da aplicação deve ser diferente do administrador." >&2
  exit 1
fi
psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v app_user="$POSTGRES_APP_USER" -v app_password="$POSTGRES_APP_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'app_user')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'app_user') \gexec
SELECT EXISTS (
  SELECT FROM pg_roles r WHERE r.rolname = :'app_user' AND (
    r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls
    OR EXISTS (SELECT FROM pg_auth_members WHERE member = r.oid)
    OR EXISTS (SELECT FROM pg_database WHERE datdba = r.oid)
    OR EXISTS (SELECT FROM pg_namespace WHERE nspowner = r.oid)
    OR EXISTS (SELECT FROM pg_class WHERE relowner = r.oid)
  )
) AS unsafe_role \gset
\if :unsafe_role
  \echo 'Use um novo usuário sem privilégios ou objetos próprios para a aplicação.'
  \quit 3
\endif
SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L', :'app_user', :'app_password') \gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_user') \gexec
SELECT format('GRANT SELECT ON TABLE route_requests, calculated_routes TO %I', :'app_user') \gexec
SELECT format('GRANT SELECT ON TABLE ocorrencias_stg TO %I', :'app_user')
WHERE to_regclass('public.ocorrencias_stg') IS NOT NULL \gexec
SELECT format('GRANT INSERT ON TABLE route_requests, calculated_routes TO %I', :'app_user') \gexec
SELECT format('GRANT USAGE, SELECT ON SEQUENCE %s TO %I', sequence_name, :'app_user')
FROM (SELECT pg_get_serial_sequence(name, 'id') AS sequence_name
      FROM (VALUES ('route_requests'), ('calculated_routes')) AS tables(name)) AS sequences
WHERE sequence_name IS NOT NULL \gexec
SQL
