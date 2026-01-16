# Equities AI Installation Guide

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+) or macOS 12+
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB available space

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD

### Software Prerequisites
- Docker 20.0 or later
- Docker Compose v2.0 or later
- curl (for installation script)
- openssl (for secret generation)

## Quick Start Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/equities-ai.git
cd equities-ai
```

### 2. Run the Installation Script

```bash
./scripts/install.sh
```

The script will:
1. Check prerequisites
2. Generate secure secrets
3. Create environment configuration
4. Build and start Docker containers
5. Run database migrations
6. Prompt for admin user creation

### 3. Access the Application

After installation completes:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Manual Installation

If you prefer manual setup:

### 1. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` and configure:
```env
# Required: Generate with `openssl rand -hex 32`
JWT_SECRET_KEY=your-secret-key-here

# Required: Strong database password
POSTGRES_PASSWORD=your-db-password

# Update for production
CORS_ORIGINS=https://your-domain.com
```

### 2. Start Services

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Run Migrations

```bash
docker-compose exec api python -m alembic -c backend/alembic.ini upgrade head
```

### 4. Create Admin User

```bash
docker-compose exec api python -c "
import asyncio
from backend.database import engine
from backend.utils.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

async def create():
    async with AsyncSession(engine) as db:
        auth = AuthService(db)
        await auth.create_user('admin@example.com', 'changeme123', 'Admin', True)
        print('Admin created')

asyncio.run(create())
"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | 30 |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | 7 |
| `REDIS_URL` | Redis connection string | redis://redis:6379/0 |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |
| `LOG_LEVEL` | Logging level | INFO |

### Ports

| Service | Default Port | Environment Variable |
|---------|--------------|---------------------|
| Frontend | 3000 | `FRONTEND_PORT` |
| API | 8000 | `API_PORT` |
| PostgreSQL | 5432 | `POSTGRES_PORT` |
| Redis | 6379 | `REDIS_PORT` |

## Verification

### Check Service Health

```bash
# Overall status
./scripts/status.sh

# API health
curl http://localhost:8000/health

# Full readiness check
curl http://localhost:8000/health/ready
```

### Verify Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme123"}'

# Use the returned token
curl http://localhost:8000/api/insights/latest \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Next Steps

1. Change the default admin password
2. Configure your domain in `CORS_ORIGINS`
3. Set up SSL/TLS (see [DEPLOYMENT.md](DEPLOYMENT.md))
4. Configure backups (see `./scripts/backup.sh`)

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
