#!/bin/bash
# Health check script for all crypto-bot services
# Usage: ./infra/scripts/healthcheck.sh
# Exit codes: 0 = all healthy, 1 = some failures

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_http_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    if response=$(curl -sf --max-time 5 -w "%{http_code}" "$url" 2>/dev/null); then
        http_code="${response: -3}"
        if [ "$http_code" = "$expected_code" ]; then
            echo -e "${GREEN}[OK]${NC} $name (HTTP $http_code)"
            return 0
        else
            echo -e "${RED}[FAIL]${NC} $name (HTTP $http_code, expected $expected_code)"
            return 1
        fi
    else
        echo -e "${RED}[FAIL]${NC} $name (connection error)"
        return 1
    fi
}

check_docker_container() {
    local name=$1
    
    if container=$(docker ps --filter "name=$name" --format "{{.Names}}" 2>/dev/null); then
        if [ -n "$container" ]; then
            status=$(docker inspect "$name" --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
            if [ "$status" = "running" ]; then
                echo -e "${GREEN}[OK]${NC} Docker container '$name' is running"
                return 0
            else
                echo -e "${RED}[FAIL]${NC} Docker container '$name' status: $status"
                return 1
            fi
        fi
    fi
    return 1
}

check_database() {
    local user=${1:-cryptobot}
    local host=${2:-localhost}
    local port=${3:-5432}
    
    if pg_isready -U "$user" -h "$host" -p "$port" > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} PostgreSQL/TimescaleDB is responding ($host:$port)"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} PostgreSQL/TimescaleDB connection failed ($host:$port)"
        return 1
    fi
}

check_minio() {
    local endpoint=${1:-localhost:9000}
    
    # MinIO health endpoint
    if curl -sf --max-time 5 "http://$endpoint/minio/health/live" > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} MinIO S3 storage is healthy ($endpoint)"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} MinIO S3 storage is unavailable ($endpoint)"
        return 1
    fi
}

echo "=========================================="
echo "  Crypto Bot Infrastructure Health Check"
echo "=========================================="
echo ""

FAILURES=0

# === HTTP Services ===
echo "HTTP Services:"
check_http_service "FastAPI Backend" "http://localhost:8000/api/v1/health" 200 || FAILURES=$((FAILURES + 1))
check_http_service "Streamlit Frontend" "http://localhost:8501" 200 || FAILURES=$((FAILURES + 1))
check_http_service "Nginx Reverse Proxy" "http://localhost/health" 200 || FAILURES=$((FAILURES + 1))
check_http_service "Prometheus" "http://localhost:9090/-/healthy" 200 || FAILURES=$((FAILURES + 1))
check_http_service "Grafana" "http://localhost:3000/api/health" 200 || FAILURES=$((FAILURES + 1))
check_http_service "MLflow Tracking" "http://localhost:5000" 200 || FAILURES=$((FAILURES + 1))

echo ""
echo "Storage & Databases:"
check_database cryptobot localhost 5432 || FAILURES=$((FAILURES + 1))
check_minio localhost:9000 || FAILURES=$((FAILURES + 1))

echo ""
echo "Docker Containers:"
check_docker_container timescaledb || FAILURES=$((FAILURES + 1))
check_docker_container minio || FAILURES=$((FAILURES + 1))
check_docker_container api || FAILURES=$((FAILURES + 1))
check_docker_container frontend || FAILURES=$((FAILURES + 1))
check_docker_container etl-worker || FAILURES=$((FAILURES + 1))
check_docker_container ml-worker || FAILURES=$((FAILURES + 1))
check_docker_container nginx || FAILURES=$((FAILURES + 1))

echo ""
echo "=========================================="
echo "  Docker Compose Status"
echo "=========================================="
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo -e "${YELLOW}[WARN]${NC} docker compose not available"

echo ""
echo "=========================================="
if [ "$FAILURES" -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS]${NC} All services are healthy"
    exit 0
else
    echo -e "${RED}[FAILURE]${NC} $FAILURES service(s) unhealthy or unreachable"
    exit 1
fi
