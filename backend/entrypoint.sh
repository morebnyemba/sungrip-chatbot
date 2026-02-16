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
        # Check if all migrations across all apps are applied
        MIGRATIONS_OUTPUT=$(python manage.py showmigrations 2>&1)
        MIGRATIONS_EXIT_CODE=$?
        
        if [ $MIGRATIONS_EXIT_CODE -ne 0 ]; then
            echo "Warning: Failed to check migrations: $MIGRATIONS_OUTPUT"
        elif [ -z "$MIGRATIONS_OUTPUT" ]; then
            echo "Warning: No migrations found in the project"
        else
            # Check if there are applied migrations and no unapplied ones
            HAS_APPLIED=$(echo "$MIGRATIONS_OUTPUT" | grep -c '\[X\]' || echo "0")
            HAS_UNAPPLIED=$(echo "$MIGRATIONS_OUTPUT" | grep -c '\[ \]' || echo "0")
            
            if [ "$HAS_APPLIED" -gt 0 ] && [ "$HAS_UNAPPLIED" -eq 0 ]; then
                echo "All migrations are complete!"
                return 0
            fi
        fi
        
        echo "Migrations not yet complete, waiting... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
    done
    
    echo "ERROR: Migrations check timed out after $((MAX_RETRIES * 2)) seconds. Cannot start service safely."
    exit 1
}

# Run migrations
if [ "$1" = "web" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput --run-syncdb
    
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
