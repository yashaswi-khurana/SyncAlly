#!/bin/sh
set -eu

: "${POSTGRES_SEEDS:?POSTGRES_SEEDS is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${SQL_PASSWORD:?SQL_PASSWORD is required}"

export PGPASSWORD="$SQL_PASSWORD"

update_database_schema() {
  database="$1"
  versioned_schema="$2"
  schema_exists=$(psql --host "$POSTGRES_SEEDS" --port "${DB_PORT:-5432}" \
    --username "$POSTGRES_USER" --dbname "$database" --tuples-only --no-align \
    --set=ON_ERROR_STOP=1 --command "SELECT to_regclass('public.schema_version') IS NOT NULL")

  if [ "$schema_exists" != "t" ]; then
    temporal-sql-tool --plugin postgres12 --ep "$POSTGRES_SEEDS" \
      -u "$POSTGRES_USER" -p "${DB_PORT:-5432}" --db "$database" setup-schema -v 0.0
  fi

  temporal-sql-tool --plugin postgres12 --ep "$POSTGRES_SEEDS" \
    -u "$POSTGRES_USER" -p "${DB_PORT:-5432}" --db "$database" \
    update-schema -d "$versioned_schema"
}

update_database_schema temporal /etc/temporal/schema/postgresql/v12/temporal/versioned
update_database_schema temporal_visibility /etc/temporal/schema/postgresql/v12/visibility/versioned
