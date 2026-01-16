#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Stopping Equities AI services..."

if [ -f "docker-compose.prod.yml" ] && [ "${USE_PROD:-1}" = "1" ]; then
    docker-compose -f docker-compose.prod.yml down
else
    docker-compose down
fi

echo "Services stopped."
