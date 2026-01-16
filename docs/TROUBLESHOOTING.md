# Equities AI Troubleshooting Guide

## Quick Diagnostics

Run the status script to get an overview:

```bash
./scripts/status.sh
```

Check logs for errors:

```bash
./scripts/logs.sh api 200
```

## Common Issues

### 1. Cannot Connect to API (Connection Refused)

**Symptoms**: `curl: (7) Failed to connect to localhost port 8000`

**Solutions**:

1. Check if containers are running:
   ```bash
   docker-compose ps
   ```

2. Check API logs:
   ```bash
   ./scripts/logs.sh api
   ```

3. Verify port binding:
   ```bash
   netstat -tlnp | grep 8000
   ```

4. Restart services:
   ```bash
   ./scripts/restart.sh
   ```

### 2. Database Connection Failed

**Symptoms**: `Connection refused` or `could not connect to server`

**Solutions**:

1. Check database container:
   ```bash
   docker-compose ps postgres
   ```

2. Check database logs:
   ```bash
   ./scripts/logs.sh postgres
   ```

3. Verify credentials in `.env` match docker-compose

4. Test connection:
   ```bash
   docker-compose exec postgres psql -U equities -d equities_ai -c "SELECT 1"
   ```

### 3. Authentication Errors (401 Unauthorized)

**Symptoms**: API returns `{"detail":"Not authenticated"}`

**Solutions**:

1. Verify you're including the token:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/...
   ```

2. Check token expiration - get a new token:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"your@email.com","password":"yourpassword"}'
   ```

3. Verify `JWT_SECRET_KEY` hasn't changed (would invalidate all tokens)

### 4. CORS Errors

**Symptoms**: Browser console shows `Access-Control-Allow-Origin` errors

**Solutions**:

1. Check `CORS_ORIGINS` in `.env`:
   ```bash
   grep CORS_ORIGINS .env
   ```

2. Add your frontend URL to CORS_ORIGINS:
   ```env
   CORS_ORIGINS=http://localhost:3000,https://your-domain.com
   ```

3. Restart API:
   ```bash
   docker-compose restart api
   ```

### 5. Migration Errors

**Symptoms**: Alembic errors during startup or migration

**Solutions**:

1. Check current migration state:
   ```bash
   docker-compose exec api python -m alembic -c backend/alembic.ini current
   ```

2. View migration history:
   ```bash
   docker-compose exec api python -m alembic -c backend/alembic.ini history
   ```

3. If database is out of sync, mark current state:
   ```bash
   docker-compose exec api python -m alembic -c backend/alembic.ini stamp head
   ```

### 6. Out of Memory

**Symptoms**: Containers killed, `OOMKilled` in docker events

**Solutions**:

1. Check memory usage:
   ```bash
   docker stats
   ```

2. Increase system memory or adjust container limits in `docker-compose.prod.yml`

3. Restart containers:
   ```bash
   ./scripts/restart.sh
   ```

### 7. Slow Performance

**Symptoms**: API responses taking > 1 second

**Solutions**:

1. Check resource usage:
   ```bash
   docker stats
   ```

2. Check database query performance:
   ```bash
   docker-compose exec postgres psql -U equities -d equities_ai \
     -c "SELECT * FROM pg_stat_activity WHERE state = 'active'"
   ```

3. Check Redis connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

4. Review logs for slow queries:
   ```bash
   ./scripts/logs.sh api | grep -i slow
   ```

### 8. WebSocket Connection Issues

**Symptoms**: Real-time updates not working

**Solutions**:

1. Check WebSocket endpoint:
   ```bash
   curl -v -H "Upgrade: websocket" -H "Connection: upgrade" \
     http://localhost:8000/ws/updates
   ```

2. If using reverse proxy, ensure WebSocket upgrade headers are passed

3. Check for connection limits on the server

## Log Analysis

### Viewing Specific Log Levels

```bash
# Errors only
./scripts/logs.sh api | grep -i error

# Warnings and above
./scripts/logs.sh api | grep -iE "error|warning|fail"
```

### Structured Log Fields

Logs are in JSON format. Use `jq` to parse:

```bash
./scripts/logs.sh api | jq 'select(.level == "error")'
```

## Database Recovery

### Restore from Backup

```bash
# List available backups
./scripts/restore.sh

# Restore specific backup
./scripts/restore.sh backups/equities_ai_20240115_020000.sql.gz
```

### Reset Database (Development Only)

```bash
# Drop and recreate database
docker-compose exec postgres psql -U equities -c "DROP DATABASE equities_ai"
docker-compose exec postgres psql -U equities -c "CREATE DATABASE equities_ai"

# Re-run migrations
docker-compose exec api python -m alembic -c backend/alembic.ini upgrade head
```

## Getting Help

1. Check this documentation
2. Review application logs: `./scripts/logs.sh`
3. Check health endpoints: `curl http://localhost:8000/health/detailed`
4. File an issue with:
   - Error messages
   - Log output
   - Steps to reproduce
   - Environment details (OS, Docker version)

## Debug Mode

For more verbose logging, set in `.env`:

```env
LOG_LEVEL=DEBUG
```

Then restart:

```bash
./scripts/restart.sh
```

Remember to set back to `INFO` for production!
