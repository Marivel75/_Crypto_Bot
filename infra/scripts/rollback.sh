#!/bin/bash
# Rollback to previous Docker Compose state
# Usage: ./infra/scripts/rollback.sh
# This stops current services and restores from git

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}=== Docker Compose Rollback ===${NC}"
echo ""
echo "Current git status:"
git status --short
echo ""

# Confirm rollback
read -p "Proceed with rollback? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo "Backing up current state..."
docker compose ps > /tmp/compose_state_before.txt
docker compose logs --tail=100 > /tmp/compose_logs_before.txt

echo "Rolling back docker-compose.yml..."
git checkout docker-compose.yml

echo "Stopping current services..."
docker compose down

echo "Starting rolled-back services..."
docker compose up -d

echo "Waiting for services..."
sleep 10

echo "Running health check..."
if ./infra/scripts/healthcheck.sh; then
    echo -e "${GREEN}✓ Rollback successful${NC}"
    exit 0
else
    echo -e "${RED}✗ Rollback health check failed${NC}"
    echo "Logs saved to /tmp/compose_logs_before.txt"
    exit 1
fi
