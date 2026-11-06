#!/bin/sh
set -eu

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 \
  --set=syncally_password="$SYNCALLY_DB_PASSWORD" \
  --set=temporal_password="$TEMPORAL_DB_PASSWORD" <<'SQL'
CREATE ROLE syncally LOGIN PASSWORD :'syncally_password';
CREATE DATABASE syncally OWNER syncally;
CREATE ROLE temporal LOGIN PASSWORD :'temporal_password';
CREATE DATABASE temporal OWNER temporal;
CREATE DATABASE temporal_visibility OWNER temporal;
SQL
