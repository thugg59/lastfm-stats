#!/bin/bash

set -euo pipefail

python3 scripts/setup_timezone.py

# setup_timezone.py just wrote DB_TIMEZONE into .env — source now to pick it up.
set -a
source .env
set +a

export PGPASSWORD="$DB_PASSWORD"

db_exists=$(psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d postgres \
  -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")

if [[ "$db_exists" != "1" ]]; then
  createdb \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    "$DB_NAME"

  echo "Database created: $DB_NAME"
else
  echo "Database already exists: $DB_NAME"
fi

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -f sql/02-schema.sql

echo "Schema setup completed successfully."

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -c "ALTER DATABASE \"$DB_NAME\" SET timezone TO '$DB_TIMEZONE';"

echo "Database timezone configured: $DB_TIMEZONE"

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -f sql/views.sql

echo "Analytics views applied successfully."