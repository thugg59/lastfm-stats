#!/bin/bash
set -euo pipefail

python3 scripts/setup_timezone.py

# Docker Compose reads .env automatically for ${VAR} substitution,
# so DB_TIMEZONE written above is picked up by db's environment block.
docker compose build pipeline
docker compose up -d --wait db

# setup_timezone.py wrote DB_TIMEZONE into .env — source now to pick up
# DB_USER/DB_NAME as well, needed for the psql call below.
set -a
source .env
set +a

docker compose exec -T db psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_NAME" < sql/views.sql

echo "Analytics views applied successfully."