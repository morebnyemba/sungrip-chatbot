#!/bin/bash

# Sungrip Solar Chatbot - Database Reset Script
# Use this script when you've changed database credentials in .env
# and need to delete the old database volume to start fresh.
#
# WARNING: This will DELETE all data in the PostgreSQL database and Redis cache.

set -e

echo "========================================="
echo "Sungrip Solar Chatbot - Database Reset"
echo "========================================="
echo ""
echo "⚠️  WARNING: This will permanently delete ALL data in:"
echo "    - PostgreSQL database (postgres_data volume)"
echo "    - Redis cache (redis_data volume)"
echo ""
read -p "Are you sure you want to continue? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ Aborted."
    exit 0
fi

echo ""
echo "🛑 Stopping all containers..."
docker compose down

echo ""
echo "🗑️  Removing database and Redis volumes..."
docker volume rm sungrip-chatbot_postgres_data sungrip-chatbot_redis_data 2>/dev/null || \
docker volume rm sungrip_chatbot_postgres_data sungrip_chatbot_redis_data 2>/dev/null || \
docker compose down -v

echo ""
echo "🐳 Starting services with fresh database..."
docker compose up -d

echo ""
echo "⏳ Waiting for database to be ready..."
retries=0
until docker compose exec -T db pg_isready -U "${DB_USER:-sungrip_user}" 2>/dev/null; do
    retries=$((retries + 1))
    if [ "$retries" -ge 30 ]; then
        echo "❌ Database did not become ready in time. Check 'docker compose logs db' for details."
        exit 1
    fi
    sleep 2
done
echo "✅ Database is ready!"

echo ""
echo "📦 Running database migrations..."
docker compose exec -T backend python manage.py migrate --noinput

echo ""
echo "🔧 Collecting static files..."
docker compose exec -T backend python manage.py collectstatic --noinput --clear

echo ""
echo "👤 Creating superuser..."
echo "Please enter new superuser credentials:"
docker compose exec backend python manage.py createsuperuser

echo ""
echo "========================================="
echo "✅ Database Reset Complete!"
echo "========================================="
echo ""
echo "Your database has been recreated with the credentials from .env"
echo "All previous data has been removed."
echo ""
