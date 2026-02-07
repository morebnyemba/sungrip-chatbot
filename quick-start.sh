#!/bin/bash

# Sungrip Solar Chatbot - Quick Start Script
# This script helps you get the application up and running quickly

set -e

echo "========================================="
echo "Sungrip Solar Chatbot - Quick Start"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your configuration."
    echo ""
    echo "Required configuration:"
    echo "  - Database credentials (DB_PASSWORD)"
    echo "  - Redis password (REDIS_PASSWORD)"
    echo "  - Django secret key (SECRET_KEY)"
    echo "  - WhatsApp API credentials"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "🐳 Starting Docker containers..."
docker compose up -d

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 10

echo ""
echo "📦 Running database migrations..."
docker compose exec -T backend python manage.py migrate

echo ""
echo "🔧 Collecting static files..."
docker compose exec -T backend python manage.py collectstatic --noinput

echo ""
echo "👤 Creating superuser..."
echo "Please enter superuser credentials:"
docker compose exec backend python manage.py createsuperuser

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "Access your application:"
echo "  - Frontend: http://localhost"
echo "  - Admin Panel: http://localhost/admin"
echo "  - API: http://localhost/api"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose logs -f"
echo "  - Stop: docker compose down"
echo "  - Restart: docker compose restart"
echo ""
echo "Next steps:"
echo "  1. Log in to admin panel with superuser credentials"
echo "  2. Configure WhatsApp settings in admin"
echo "  3. Start receiving messages!"
echo ""
