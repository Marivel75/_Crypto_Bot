#!/bin/bash
# scripts/backup-db.sh — TimescaleDB backup with 30-day retention
set -euo pipefail
umask 077

# Validate required environment variables
: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_DB:?POSTGRES_DB is not set}"

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups/timescaledb

mkdir -p -m 700 "$BACKUP_DIR"

# Verify the container is running before attempting backup
if ! docker inspect --format '{{.State.Running}}' timescaledb 2>/dev/null | grep -q true; then
  echo "ERROR: timescaledb container is not running" >&2
  exit 1
fi

# Atomic write: dump to .tmp, rename on success
TMP="$BACKUP_DIR/cryptobot_$DATE.sql.gz.tmp"
docker exec timescaledb pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$TMP" \
  && mv "$TMP" "$BACKUP_DIR/cryptobot_$DATE.sql.gz"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

logger -t backup-db "Backup done: cryptobot_$DATE.sql.gz"
