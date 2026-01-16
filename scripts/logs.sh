#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

SERVICE="${1:-}"
LINES="${2:-100}"

show_help() {
    echo "Usage: ./scripts/logs.sh [service] [lines]"
    echo ""
    echo "Services:"
    echo "  api      - API server logs"
    echo "  postgres - Database logs"
    echo "  redis    - Redis logs"
    echo "  frontend - Frontend logs"
    echo "  (empty)  - All services"
    echo ""
    echo "Options:"
    echo "  lines    - Number of lines to show (default: 100)"
    echo ""
    echo "Examples:"
    echo "  ./scripts/logs.sh           # All logs"
    echo "  ./scripts/logs.sh api       # API logs only"
    echo "  ./scripts/logs.sh api 500   # Last 500 API log lines"
}

if [ "$SERVICE" = "-h" ] || [ "$SERVICE" = "--help" ]; then
    show_help
    exit 0
fi

COMPOSE_FILE="docker-compose.yml"
if [ -f "docker-compose.prod.yml" ] && [ "${USE_PROD:-1}" = "1" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

if [ -z "$SERVICE" ]; then
    docker-compose -f "$COMPOSE_FILE" logs --tail="$LINES" -f
else
    docker-compose -f "$COMPOSE_FILE" logs --tail="$LINES" -f "$SERVICE"
fi
