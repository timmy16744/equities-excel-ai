#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$PROJECT_DIR"

echo "=============================================="
echo "  Equities AI Service Status"
echo "=============================================="
echo ""

# Determine compose file
COMPOSE_FILE="docker-compose.yml"
if [ -f "docker-compose.prod.yml" ] && [ "${USE_PROD:-1}" = "1" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

echo "Container Status:"
echo "-----------------"
docker-compose -f "$COMPOSE_FILE" ps
echo ""

echo "Health Checks:"
echo "--------------"

# API health
API_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ -n "$API_HEALTH" ]; then
    echo -e "API:      ${GREEN}healthy${NC}"
    echo "          $API_HEALTH"
else
    echo -e "API:      ${RED}unreachable${NC}"
fi

# API readiness
API_READY=$(curl -s http://localhost:8000/health/ready 2>/dev/null)
if [ -n "$API_READY" ]; then
    READY_STATUS=$(echo "$API_READY" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$READY_STATUS" = "ready" ]; then
        echo -e "Ready:    ${GREEN}$READY_STATUS${NC}"
    else
        echo -e "Ready:    ${YELLOW}$READY_STATUS${NC}"
    fi
else
    echo -e "Ready:    ${RED}unknown${NC}"
fi

# Frontend
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "Frontend: ${GREEN}healthy${NC}"
else
    echo -e "Frontend: ${YELLOW}status code $FRONTEND_STATUS${NC}"
fi

echo ""
echo "Resource Usage:"
echo "---------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -5

echo ""
echo "Logs (recent errors):"
echo "---------------------"
docker-compose -f "$COMPOSE_FILE" logs --tail=5 2>&1 | grep -i "error\|exception\|fail" | tail -5 || echo "No recent errors found"
