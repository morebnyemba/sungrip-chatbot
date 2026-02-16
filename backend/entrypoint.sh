#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! pg_isready -h ${DB_HOST:-db} -p ${DB_PORT:-5432} -U ${DB_USER:-sungrip_user}; do
  sleep 1
done
echo "Database is ready!"

# Function to wait for migrations to complete
wait_for_migrations() {
    echo "Waiting for migrations to complete..."
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        # Check if django_celery_beat tables exist
        if python manage.py showmigrations django_celery_beat 2>/dev/null | grep -q '\[X\]'; then
            echo "Migrations are complete!"
            return 0
        fi
        
        echo "Migrations not yet complete, waiting... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
    done
    
    echo "Warning: Migrations check timed out after $MAX_RETRIES attempts"
    return 1
}

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
    wait_for_migrations
    echo "Starting Celery worker..."
    exec celery -A sungrip_backend worker \
        --loglevel=info \
        --pool=gevent \
        --concurrency=20
elif [ "$1" = "celery_beat" ]; then
    wait_for_migrations
    echo "Starting Celery beat..."
    exec celery -A sungrip_backend beat \
        --loglevel=info \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
    exec "$@"
fi
