# Equities AI Deployment Guide

This guide covers production deployment best practices.

## Pre-Deployment Checklist

- [ ] Generate strong secrets (`openssl rand -hex 32`)
- [ ] Set strong database password
- [ ] Configure domain in `CORS_ORIGINS`
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Test backup and restore procedures

## Production Configuration

### 1. Use Production Compose File

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Key differences from development:
- Resource limits on containers
- Network isolation (database not exposed)
- Log rotation configured
- Healthcheck intervals optimized

### 2. Essential Environment Variables

Create `.env` with production values:

```env
# Security - REQUIRED: Change these!
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
POSTGRES_PASSWORD=<strong-random-password>

# CORS - Update with your domain
CORS_ORIGINS=https://your-domain.com

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## SSL/TLS Configuration

### Option A: Caddy (Recommended - Automatic HTTPS)

Create `Caddyfile`:
```
your-domain.com {
    reverse_proxy frontend:80

    handle /api/* {
        reverse_proxy api:8000
    }

    handle /ws/* {
        reverse_proxy api:8000
    }

    handle /health* {
        reverse_proxy api:8000
    }
}
```

Add to docker-compose:
```yaml
caddy:
  image: caddy:2-alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile
    - caddy_data:/data
    - caddy_config:/config
  networks:
    - frontend
```

### Option B: Nginx with Let's Encrypt

Create `nginx.conf`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /health {
        proxy_pass http://api:8000;
    }
}
```

## Firewall Configuration

### UFW (Ubuntu)

```bash
# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable
```

### iptables

```bash
# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Drop everything else
iptables -A INPUT -j DROP
```

## Backup Strategy

### Automated Backups

Create a cron job for regular backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/equities-ai/scripts/backup.sh >> /var/log/equities-backup.log 2>&1
```

### Off-site Backup

Sync backups to cloud storage:

```bash
# AWS S3
aws s3 sync /path/to/equities-ai/backups s3://your-bucket/equities-backups/

# rsync to remote server
rsync -avz /path/to/equities-ai/backups/ user@backup-server:/backups/
```

## Monitoring

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic liveness |
| `/health/live` | Kubernetes liveness probe |
| `/health/ready` | Kubernetes readiness probe |
| `/health/detailed` | Full system status |

### Example Monitoring Script

```bash
#!/bin/bash
HEALTH=$(curl -s http://localhost:8000/health/ready)
STATUS=$(echo "$HEALTH" | jq -r '.status')

if [ "$STATUS" != "ready" ]; then
    echo "Alert: Equities AI is not ready"
    # Send alert via email, Slack, PagerDuty, etc.
fi
```

## Scaling

### Horizontal Scaling

For high availability, deploy multiple API instances:

```yaml
api:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
    restart_policy:
      condition: on-failure
```

Use a load balancer (nginx, HAProxy, or cloud LB) to distribute traffic.

### Database Scaling

For larger deployments:
- Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
- Configure read replicas
- Enable connection pooling (PgBouncer)

## Upgrade Procedure

1. **Backup database**
   ```bash
   ./scripts/backup.sh
   ```

2. **Pull latest code**
   ```bash
   git pull origin main
   ```

3. **Rebuild containers**
   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```

4. **Run migrations**
   ```bash
   docker-compose exec api python -m alembic -c backend/alembic.ini upgrade head
   ```

5. **Restart services**
   ```bash
   ./scripts/restart.sh
   ```

6. **Verify health**
   ```bash
   ./scripts/status.sh
   ```

## Rollback Procedure

If issues occur after upgrade:

1. **Stop services**
   ```bash
   ./scripts/stop.sh
   ```

2. **Restore database**
   ```bash
   ./scripts/restore.sh backups/equities_ai_TIMESTAMP.sql.gz
   ```

3. **Checkout previous version**
   ```bash
   git checkout <previous-tag>
   ```

4. **Rebuild and start**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```
