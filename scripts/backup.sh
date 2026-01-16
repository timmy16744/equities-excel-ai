#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

POSTGRES_USER="${POSTGRES_USER:-equities}"
POSTGRES_DB="${POSTGRES_DB:-equities_ai}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/equities_ai_${TIMESTAMP}.sql.gz"

echo "Creating database backup..."

cd "$PROJECT_DIR"

# Determine container name based on compose file
CONTAINER="equities-ai-postgres"
if ! docker ps --format '{{.Names}}' | grep -q "$CONTAINER"; then
    CONTAINER="equities-ai-db"
fi

# Create backup using pg_dump
docker exec "$CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

# Verify backup was created
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}Backup created successfully!${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"

    # Clean up old backups (keep last 10)
    cd "$BACKUP_DIR"
    ls -t equities_ai_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm --
    BACKUP_COUNT=$(ls -1 equities_ai_*.sql.gz 2>/dev/null | wc -l)
    echo "  Total backups: $BACKUP_COUNT"
else
    echo -e "${RED}Backup failed!${NC}"
    exit 1
fi
