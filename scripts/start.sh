#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting Equities AI services..."

if [ -f "docker-compose.prod.yml" ] && [ "${USE_PROD:-1}" = "1" ]; then
    docker-compose -f docker-compose.prod.yml up -d
else
    docker-compose up -d
fi

echo "Services started. Waiting for health checks..."
sleep 5

# Check health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is healthy!"
else
    echo "Warning: API health check failed. Check logs with: ./scripts/logs.sh api"
fi

echo ""
echo "Services are running:"
echo "  - Frontend: http://localhost:3000"
echo "  - API:      http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
