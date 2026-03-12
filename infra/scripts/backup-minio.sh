#!/bin/bash
# Backup MinIO buckets daily
# Usage: ./backup-minio.sh [--restore-from PATH]
# Cron: 0 2 * * * cd /path/to/cryptobot && infra/scripts/backup-minio.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="/backups/minio"
MINIO_ALIAS="local"
DOCKER_COMPOSE_DIR="$PROJECT_ROOT"
RETENTION_DAYS=30

# Parse arguments
RESTORE_MODE=false
RESTORE_FROM=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --restore-from)
            RESTORE_MODE=true
            RESTORE_FROM="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

if [ "$RESTORE_MODE" = true ]; then
    # Restore from backup
    if [ -z "$RESTORE_FROM" ] || [ ! -d "$RESTORE_FROM" ]; then
        log_error "Invalid restore path: $RESTORE_FROM"
        exit 1
    fi
    
    log_info "Restoring MinIO buckets from: $RESTORE_FROM"
    
    # Run mc mirror to restore (requires mc client in container)
    docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" run --rm \
        -v "$RESTORE_FROM:/backup:ro" \
        minio \
        mc mirror /backup/ local/ --overwrite --remove
    
    log_info "Restore completed successfully"
    exit 0
fi

# Regular backup mode
log_info "Starting MinIO backup to $BACKUP_DIR"

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/minio_backup_$BACKUP_DATE"

mkdir -p "$BACKUP_PATH"

# Get list of buckets
log_info "Fetching bucket list..."
BUCKETS=$(docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" exec -T minio mc ls local/ | awk '{print $NF}' | sed 's/\///')

if [ -z "$BUCKETS" ]; then
    log_warn "No buckets found in MinIO"
    exit 0
fi

# Backup each bucket
BUCKET_COUNT=0
for bucket in $BUCKETS; do
    BUCKET_BACKUP="$BACKUP_PATH/$bucket"
    mkdir -p "$BUCKET_BACKUP"
    
    log_info "Backing up bucket: $bucket → $BUCKET_BACKUP"
    
    # Use mc mirror to backup bucket contents
    docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" exec -T minio \
        mc mirror --quiet local/"$bucket" /minio/backup/"$bucket" || {
        log_error "Failed to backup bucket: $bucket"
        continue
    }
    
    # Copy backup out of container
    docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" cp \
        minio:/minio/backup/"$bucket" "$BUCKET_BACKUP" || {
        log_warn "Could not copy from container, trying alternative method"
        # Alternative: use s3 protocol
        docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" run --rm \
            -v "$BUCKET_BACKUP:/backup" \
            minio \
            mc mirror --quiet local/"$bucket" /backup/
    }
    
    BUCKET_SIZE=$(du -sh "$BUCKET_BACKUP" 2>/dev/null | cut -f1)
    log_info "  ✓ Completed: $BUCKET_SIZE"
    ((BUCKET_COUNT++))
done

TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
log_info "Backup completed: $BUCKET_COUNT buckets, $TOTAL_SIZE"

# Compress backup
log_info "Compressing backup..."
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "minio_backup_$BACKUP_DATE" && \
    rm -rf "$BACKUP_PATH" && \
    log_info "  ✓ Compressed: $(du -sh "$BACKUP_PATH.tar.gz" | cut -f1)"

# Cleanup old backups (keep 30 days)
log_info "Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "minio_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
OLD_BACKUP_COUNT=$(find "$BACKUP_DIR" -name "minio_backup_*.tar.gz" | wc -l)
log_info "  ✓ Retained: $OLD_BACKUP_COUNT recent backups"

log_info "MinIO backup completed successfully"
log_info "Restore with: $SCRIPT_DIR/backup-minio.sh --restore-from $BACKUP_PATH"
