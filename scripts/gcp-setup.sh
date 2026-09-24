#!/bin/bash

set -euo pipefail

python3 scripts/setup_timezone.py

# setup_timezone.py wrote DB_TIMEZONE into .env - source it now.
set -a
source .env
set +a

export PGPASSWORD="$DB_PASSWORD"

echo "Testing PostgreSQL connection..."

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -c "SELECT current_database(), current_user;"

echo "PostgreSQL connection successful."

echo "Applying database schema..."

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -f sql/02-schema.sql

echo "Schema setup completed successfully."

echo "Configuring database timezone..."

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -c "ALTER DATABASE \"$DB_NAME\" SET timezone TO '$DB_TIMEZONE';"

echo "Database timezone configured: $DB_TIMEZONE"

echo "Applying analytics views..."

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -q \
  -v ON_ERROR_STOP=1 \
  -f sql/views.sql

echo "Analytics views applied successfully."

echo "GCP database setup completed successfully."