#!/bin/bash
# Runs once, on first container init, via docker-entrypoint-initdb.d.

set -e

if [ -z "$DB_TIMEZONE" ]; then
  echo "DB_TIMEZONE not set; skipping timezone configuration (using image default)."
  exit 0
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER DATABASE "$POSTGRES_DB" SET timezone TO '$DB_TIMEZONE';
EOSQL

echo "Database timezone set to $DB_TIMEZONE"