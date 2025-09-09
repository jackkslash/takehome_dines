# EPOS - Electronic Point of Sale System

A Django-based EPOS system with PostgreSQL and Redis.

## Quick Start

1. **Copy environment file**
   ```bash
   cp env.example .env
   ```

2. **Start with Docker**
   ```bash
   docker-compose up --build
   ```

3. **Run migrations**
   ```bash
   docker-compose exec web uv run manage.py migrate
   ```

4. **Access the app**
   - API: http://localhost:8000/api/
   - Admin: http://localhost:8000/admin/

## Environment Variables

Edit `.env` file with your settings:

```env
POSTGRES_DB=epos_db
POSTGRES_USER=epos_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Tech Stack

- Django 5.2.6
- PostgreSQL
- Redis
- Docker
- UV package manager

