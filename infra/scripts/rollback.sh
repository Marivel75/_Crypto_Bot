#!/bin/bash
# Database and image rollback script
# Usage: ./rollback.sh [VERSION]
# Example: ./rollback.sh v1.2.3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_COMPOSE_DIR="$PROJECT_ROOT"
BACKUP_DIR="/backups"
IMAGES_DIR="/backups/images"
VERSION="${1:-latest}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

confirm() {
    local prompt="$1"
    local response
    read -p "$(echo -e ${YELLOW}$prompt${NC}) " response
    [[ "$response" =~ ^[Yy]$ ]]
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "=== Crypto Bot Rollback Utility ==="
log_info "Rolling back to version: $VERSION"
log_info ""

# List available backups
if [ "$VERSION" = "latest" ]; then
    log_info "Available database backups:"
    ls -lhS "$BACKUP_DIR"/pre-deploy-*.sql.gz 2>/dev/null | tail -5 || {
        log_error "No database backups found in $BACKUP_DIR"
        exit 1
    }
    
    # Use most recent backup
    LATEST_BACKUP=$(ls -1t "$BACKUP_DIR"/pre-deploy-*.sql.gz | head -1)
    log_info "Using latest backup: $(basename $LATEST_BACKUP)"
    VERSION=$(basename "$LATEST_BACKUP" | sed 's/pre-deploy-//;s/.sql.gz//')
else
    LATEST_BACKUP="$BACKUP_DIR/pre-deploy-$VERSION.sql.gz"
    if [ ! -f "$LATEST_BACKUP" ]; then
        log_error "Backup not found: $LATEST_BACKUP"
        exit 1
    fi
fi

log_info ""
log_warn "WARNING: This will restore the database to backup timestamp: $VERSION"
log_warn "All database changes since this backup will be lost."
log_warn ""

if ! confirm "Do you want to continue? (yes/no)"; then
    log_info "Rollback cancelled"
    exit 0
fi

# Stop services
log_info "Stopping services..."
docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" down

log_info "Waiting 5 seconds before restoring database..."
sleep 5

# Restore database
log_info "Restoring database from backup: $LATEST_BACKUP"
zcat "$LATEST_BACKUP" | docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" run \
    --rm timescaledb psql -U cryptobot -d cryptobot || {
    log_error "Database restore failed!"
    exit 1
}

log_info "  ✓ Database restored"

# Restart services
log_info "Restarting services..."
docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" up -d

log_info "Waiting for services to be healthy..."
sleep 10

# Health checks
RETRIES=5
for i in $(seq 1 $RETRIES); do
    if curl -sf http://localhost:8000/health > /dev/null; then
        log_info "  ✓ API is healthy"
        break
    fi
    if [ $i -lt $RETRIES ]; then
        log_warn "  Attempt $i/$RETRIES: Waiting for API to be healthy..."
        sleep 5
    fi
done

if ! curl -sf http://localhost:8000/health > /dev/null; then
    log_error "API failed to recover. Manual intervention required."
    exit 1
fi

log_info ""
log_info "=== Rollback Completed Successfully ==="
log_info "Database restored from: $(basename $LATEST_BACKUP)"
log_info "Services are running and healthy"
log_info ""
log_info "Next steps:"
log_info "1. Verify data integrity: docker compose logs api"
log_info "2. Check business metrics in frontend"
log_info "3. Review any failed transactions"
log_info "4. Report the incident and begin investigation"
