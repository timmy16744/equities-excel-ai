#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

POSTGRES_USER="${POSTGRES_USER:-equities}"
POSTGRES_DB="${POSTGRES_DB:-equities_ai}"

show_help() {
    echo "Usage: ./scripts/restore.sh [backup_file]"
    echo ""
    echo "If no backup file is specified, lists available backups."
    echo ""
    echo "Examples:"
    echo "  ./scripts/restore.sh                                    # List backups"
    echo "  ./scripts/restore.sh backups/equities_ai_20240115.sql.gz  # Restore specific backup"
}

list_backups() {
    echo "Available backups:"
    echo ""
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
        if [ $? -ne 0 ]; then
            echo "  No backups found in $BACKUP_DIR"
        fi
    else
        echo "  Backup directory does not exist: $BACKUP_DIR"
    fi
    echo ""
    echo "To restore, run: ./scripts/restore.sh <backup_file>"
}

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    list_backups
    exit 0
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}WARNING: This will overwrite the current database!${NC}"
read -p "Are you sure you want to restore from $BACKUP_FILE? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

cd "$PROJECT_DIR"

# Determine container name
CONTAINER="equities-ai-postgres"
if ! docker ps --format '{{.Names}}' | grep -q "$CONTAINER"; then
    CONTAINER="equities-ai-db"
fi

echo "Restoring database..."

# Drop and recreate database
docker exec "$CONTAINER" psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
docker exec "$CONTAINER" psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"

# Restore from backup
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo -e "${GREEN}Database restored successfully from: $BACKUP_FILE${NC}"
echo ""
echo "You may need to restart services: ./scripts/restart.sh"
