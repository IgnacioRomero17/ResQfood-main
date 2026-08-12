#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn resqfood.wsgi --preload --workers 2 --timeout 120 --bind 0.0.0.0:10000
