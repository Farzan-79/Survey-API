#!/bin/sh
set -e

echo "Waiting for the database to be ready..."
until python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveyapi.settings')
django.setup()
from django.db import connections
connections['default'].cursor()
" > /dev/null 2>&1; do
    sleep 1
done

echo "Database is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"