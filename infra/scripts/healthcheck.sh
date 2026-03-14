#!/bin/bash
# Health check script for all crypto-bot services
# Usage: ./infra/scripts/healthcheck.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} $name"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $name"
        return 1
    fi
}

echo "=== Crypto Bot Health Check ==="
echo ""

FAILURES=0

check_service "API"       "http://localhost:8000/health"     || FAILURES=$((FAILURES + 1))
check_service "Frontend"  "http://localhost:8501"             || FAILURES=$((FAILURES + 1))
check_service "MinIO"     "http://localhost:9000/minio/health/live" || FAILURES=$((FAILURES + 1))
check_service "Nginx"     "http://localhost/health"           || FAILURES=$((FAILURES + 1))

echo ""

# Check Docker containers
echo "=== Docker Containers ==="
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "docker compose not available"

echo ""

if [ "$FAILURES" -gt 0 ]; then
    echo -e "${RED}$FAILURES service(s) unhealthy${NC}"
    exit 1
else
    echo -e "${GREEN}All services healthy${NC}"
    exit 0
fi
