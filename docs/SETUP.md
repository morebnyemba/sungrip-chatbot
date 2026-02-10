# Sungrip Solar Chatbot - Setup & Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [WhatsApp Configuration](#whatsapp-configuration)
5. [Environment Variables](#environment-variables)
6. [Database Setup](#database-setup)
7. [Dependency Management](#dependency-management)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Docker Desktop (recommended) or Docker + Docker Compose
- Git
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- PostgreSQL 15+ (if running locally without Docker)
- Redis 7+ (if running locally without Docker)

### Required Accounts
- Meta/Facebook Developer Account (for WhatsApp Business API)
- WhatsApp Business Account
- Google Cloud Account (optional, for AI features)

## Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/morebnyemba/sungrip-chatbot.git
cd sungrip-chatbot
```

### 2. Create Environment File
```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Environment Variables](#environment-variables)).

### 3. Backend Setup (Without Docker)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver
```

The backend will be available at http://localhost:8000

### 4. Frontend Setup (To be implemented)

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Run migrations
docker compose exec backend python manage.py migrate

# Create superuser
docker compose exec backend python manage.py createsuperuser

# Collect static files
docker compose exec backend python manage.py collectstatic --noinput
```

### Individual Service Commands

```bash
# Start only database
docker compose up -d db

# Start only backend
docker compose up -d backend

# Restart a service
docker compose restart backend

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v
```

### Access Services

- **Frontend**: http://localhost
- **Backend API**: http://localhost/api
- **Django Admin**: http://localhost/admin
- **Database**: localhost:5432
- **Redis**: localhost:6379

## WhatsApp Configuration

### 1. Create WhatsApp Business App

1. Go to https://developers.facebook.com
2. Create a new app
3. Add "WhatsApp" product
4. Configure WhatsApp Business API

### 2. Get Credentials

From the WhatsApp Business API dashboard, collect:

- **Phone Number ID**: Found in "API Setup" section
- **Business Account ID**: Found in app dashboard
- **Access Token**: Generate a permanent token (24hr tokens expire)
- **App Secret**: Found in Basic Settings

### 3. Configure Webhook

1. In the WhatsApp dashboard, go to Configuration
2. Set Webhook URL: `https://yourdomain.com/webhook/`
3. Set Verify Token: Use the same value as `WHATSAPP_VERIFY_TOKEN` in your `.env`
4. Subscribe to `messages` events

### 4. Update Environment Variables

```env
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
WHATSAPP_APP_SECRET=your_app_secret
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
```

### 5. Test Webhook

```bash
# Verify webhook is working
curl -X GET "https://yourdomain.com/webhook/?hub.mode=subscribe&hub.verify_token=your_verify_token&hub.challenge=test_challenge"

# Should return: test_challenge
```

## Environment Variables

### Required Variables

```env
# Database
DB_NAME=sungrip_db
DB_USER=sungrip_user
DB_PASSWORD=<generate-secure-password>
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_PASSWORD=<generate-secure-password>
CELERY_BROKER_URL=redis://:your_redis_password@redis:6379/0

# Django
SECRET_KEY=<generate-secret-key>  # Use: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=False  # Set to True only in development
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# WhatsApp
WHATSAPP_PHONE_NUMBER_ID=<from-meta-dashboard>
WHATSAPP_ACCESS_TOKEN=<from-meta-dashboard>
WHATSAPP_APP_SECRET=<from-meta-dashboard>
WHATSAPP_VERIFY_TOKEN=<your-custom-token>
```

### Optional Variables
```env
# AI Features
GOOGLE_AI_API_KEY=<your-google-ai-key>

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<your-app-password>

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Dependency Management

### Backend (Python)

The backend uses pinned versions in [backend/requirements.txt](backend/requirements.txt).

Security audit:

```bash
cd backend
pip install pip-audit
pip-audit -r requirements.txt
```

Optional lock file for deployments:

```bash
cd backend
pip freeze > requirements-locked.txt
```

### Frontend (Node.js)

When the frontend is in use:

```bash
cd frontend
npm audit
npm audit fix
```

## Database Setup

### Using Docker (Recommended)

Database is automatically created when you run `docker compose up`.

### Manual PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
postgres=# CREATE DATABASE sungrip_db;
postgres=# CREATE USER sungrip_user WITH PASSWORD 'your_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE sungrip_db TO sungrip_user;
postgres=# \q

# Run migrations
python manage.py migrate
```

### Database Backups

```bash
# Create backup
docker compose exec db pg_dump -U sungrip_user sungrip_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker compose exec -T db psql -U sungrip_user sungrip_db < backup_20240115_120000.sql
```

## Production Deployment

### 1. Server Requirements

- **OS**: Ubuntu 20.04+ or any Linux distribution
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: 20GB+ SSD
- **CPU**: 2+ cores
- **Network**: Static IP with open ports 80 (HTTP) and 443 (HTTPS)

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

### 3. Clone and Configure

```bash
git clone https://github.com/morebnyemba/sungrip-chatbot.git
cd sungrip-chatbot

# Create production environment file
cp .env.example .env
nano .env  # Edit with production values
```

### 4. SSL Certificate Setup

#### Option A: Let's Encrypt (Free)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Certificates will be in /etc/letsencrypt/live/yourdomain.com/
```

Update `nginx_proxy/nginx.conf` to use SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

#### Option B: Custom SSL Certificate

Place your SSL certificate files in `nginx_proxy/ssl/`:
- `cert.pem` - SSL certificate
- `key.pem` - Private key

### 5. Deploy Application

```bash
# Start services
docker compose up -d

# Run migrations
docker compose exec backend python manage.py migrate

# Create superuser
docker compose exec backend python manage.py createsuperuser

# Collect static files
docker compose exec backend python manage.py collectstatic --noinput
```

### 6. Setup Auto-restart

Create systemd service `/etc/systemd/system/sungrip.service`:

```ini
[Unit]
Description=Sungrip Solar Chatbot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/sungrip-chatbot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable sungrip
sudo systemctl start sungrip
```

### 7. Setup Monitoring

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f backend

# Check service status
docker compose ps
```

### 8. Regular Maintenance

```bash
# Update application
git pull origin main
docker compose up -d --build

# Backup database (daily cron job recommended)
0 2 * * * cd /path/to/sungrip-chatbot && docker compose exec -T db pg_dump -U sungrip_user sungrip_db > /backups/sungrip_$(date +\%Y\%m\%d).sql

# Clean old images
docker system prune -a --filter "until=720h"
```

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker compose logs backend

# Common issues:
# 1. Database not ready - wait a few seconds and retry
# 2. Missing environment variables - check .env file
# 3. Port already in use - change DJANGO_PORT in .env
```

### Database Connection Error

```bash
# Test database connection
docker compose exec backend python manage.py dbshell

# Check database is running
docker compose ps db

# Restart database
docker compose restart db
```

### WhatsApp Webhook Not Working

1. **Verify webhook URL is accessible**:
   ```bash
   curl https://yourdomain.com/webhook/
   ```

2. **Check webhook logs**:
   ```bash
   docker compose logs backend | grep webhook
   ```

3. **Verify SSL certificate** (WhatsApp requires HTTPS)
4. **Check verify token** matches in `.env` and Meta dashboard

### Celery Tasks Not Running

```bash
# Check Celery worker status
docker compose logs celery_worker

# Check Redis connection
docker compose exec backend python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
```

### Static Files Not Loading

```bash
# Collect static files
docker compose exec backend python manage.py collectstatic --noinput

# Check nginx configuration
docker compose exec nginx nginx -t

# Restart nginx
docker compose restart nginx
```

### Permission Issues

```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Fix media directory permissions
docker compose exec backend chmod -R 755 /app/media
```

## Support

For additional support:
- Check logs: `docker compose logs -f`
- Review documentation in `/docs`
- Contact: support@sungrip.com
