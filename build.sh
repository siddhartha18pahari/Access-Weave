#!/usr/bin/env bash
# Vercel build: collect static assets, then prepare the database.
set -e

python -m pip install -r requirements.txt
python manage.py collectstatic --noinput

# Vercel's Supabase integration injects POSTGRES_URL; other hosts use DATABASE_URL.
DB="${DATABASE_URL:-${POSTGRES_URL:-$POSTGRES_URL_NON_POOLING}}"

if [ -n "$DB" ]; then
  echo "Database configured -> applying migrations and seeding the demo account"
  python manage.py migrate --noinput
  python manage.py seed_demo || echo "seed_demo skipped (already present)"
else
  echo "WARNING: no database URL found (DATABASE_URL / POSTGRES_URL)."
  echo "The deployment will use an ephemeral SQLite file and will NOT retain data."
fi
