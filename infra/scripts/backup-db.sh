#!/bin/bash
# Backup TimescaleDB to local gzip file
# Usage: ./infra/scripts/backup-db.sh
# Cron: 0 3 * * * /path/to/infra/scripts/backup-db.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-.}/backups"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/timescaledb_$TIMESTAMP.sql.gz"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Starting database backup to $BACKUP_FILE..."

# Backup database
if docker compose exec -T timescaledb pg_dump -U cryptobot cryptobot 2>/dev/null | \
   gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup completed: $BACKUP_FILE ($SIZE)"
else
    echo "✗ Backup failed"
    exit 1
fi

# Clean old backups (older than RETENTION_DAYS)
echo "Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "timescaledb_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete

# Show recent backups
echo "Recent backups:"
ls -lh "$BACKUP_DIR"/timescaledb_*.sql.gz | tail -5

exit 0
