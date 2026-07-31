#!/usr/bin/env bash
# Vercel build: collect static assets, then prepare the database.
set -e

python -m pip install -r requirements.txt
python manage.py collectstatic --noinput

if [ -n "$DATABASE_URL" ]; then
  echo "DATABASE_URL set -> applying migrations and seeding the demo account"
  python manage.py migrate --noinput
  python manage.py seed_demo || echo "seed_demo skipped (already present)"
else
  echo "WARNING: DATABASE_URL is not set. The deployment will use an ephemeral"
  echo "SQLite file and will NOT retain accounts or tasks between requests."
fi
