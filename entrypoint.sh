#!/usr/bin/env sh
set -e

echo "Applying migrations…"
python manage.py migrate --noinput

echo "Seeding demo account…"
python manage.py seed_demo || true

echo "Starting gunicorn on 0.0.0.0:8000…"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
