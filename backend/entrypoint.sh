#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! pg_isready -h ${DB_HOST:-db} -p ${DB_PORT:-5432} -U ${DB_USER:-sungrip_user}; do
  sleep 1
done
echo "Database is ready!"

# Run migrations
if [ "$1" = "web" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput
    
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    
    echo "Starting Gunicorn server..."
    exec gunicorn sungrip_backend.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 4 \
        --threads 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        --log-level info
elif [ "$1" = "celery_worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A sungrip_backend worker \
        --loglevel=info \
        --pool=gevent \
        --concurrency=20
elif [ "$1" = "celery_beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A sungrip_backend beat \
        --loglevel=info \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
    exec "$@"
fi
