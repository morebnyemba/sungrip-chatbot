# Database Migration Fix for Celery Services

## Problem Description

Previously, the Celery Beat and Celery Worker services would fail to start with the following error:

```
django.db.utils.ProgrammingError: relation "django_celery_beat_periodictask" does not exist
```

This occurred because of a race condition where:
1. The backend service would start running migrations
2. The celery_beat and celery_worker services would start immediately after the backend container started
3. The celery services would try to access the database before migrations completed
4. The django-celery-beat tables wouldn't exist yet, causing the error

## Solution

### Changes Made

1. **entrypoint.sh** - Added a `wait_for_migrations()` function that:
   - Polls the database using `python manage.py showmigrations django_celery_beat`
   - Waits up to 60 seconds (30 retries × 2 seconds) for migrations to complete
   - Only starts the celery service after confirming migrations are applied

2. **Dockerfile** - Updated to:
   - Copy and set execute permissions on entrypoint.sh
   - Set entrypoint.sh as the ENTRYPOINT
   - Use "web" as the default CMD

3. **docker-compose.yml** - Simplified service commands to use entrypoint modes:
   - `backend: command: web` - Runs migrations, collects static files, starts gunicorn
   - `celery_worker: command: celery_worker` - Waits for migrations, then starts worker
   - `celery_beat: command: celery_beat` - Waits for migrations, then starts beat scheduler

### How It Works

```
┌─────────────┐
│ db service  │ (healthcheck: pg_isready)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   backend   │ (runs migrations immediately)
│  (command:  │
│    web)     │
└──────┬──────┘
       │
       ├───────────────────┐
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│celery_worker│    │ celery_beat │
│  (waits for │    │ (waits for  │
│ migrations) │    │  migrations)│
└─────────────┘    └─────────────┘
```

### Testing the Fix

To test that the fix works:

1. Clean up existing containers and volumes:
   ```bash
   docker compose down -v
   ```

2. Start the services:
   ```bash
   docker compose up -d
   ```

3. Check the logs to verify the migration wait logic:
   ```bash
   # Backend should show migrations running
   docker compose logs backend
   
   # Celery services should show "Waiting for migrations..." then "Migrations are complete!"
   docker compose logs celery_beat
   docker compose logs celery_worker
   ```

4. Verify all services are running without errors:
   ```bash
   docker compose ps
   ```

All services should show "Up" status and no errors in the logs.

## Alternative Approaches Considered

1. **Health check on backend** - Docker health checks can't easily verify that migrations are complete
2. **Sleep timer** - Fixed delays are unreliable and waste time
3. **Separate migration service** - Adds complexity and another container to manage
4. **Database locking** - Could cause deadlocks and is overly complex

The polling approach was chosen because it:
- Is simple and reliable
- Has a reasonable timeout (60 seconds)
- Provides clear logging of the wait process
- Doesn't add infrastructure complexity
