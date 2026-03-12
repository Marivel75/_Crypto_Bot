#!/bin/bash
# Backup MinIO S3 objects
# Usage: ./infra/scripts/backup-minio.sh
# Requires: minio/mc (MinIO client)
# Install: docker run minio/mc:latest mc version

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-.}/backups"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_USER="${MINIO_USER:-minioadmin}"
MINIO_PASS="${MINIO_PASS:-minioadmin}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/minio_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "Starting MinIO backup..."

# Use docker run to execute mc
docker run --rm \
  -e MINIO_ROOT_USER="$MINIO_USER" \
  -e MINIO_ROOT_PASSWORD="$MINIO_PASS" \
  --network host \
  minio/mc:latest \
  mirror \
  --region us-east-1 \
  minio/"$MINIO_ENDPOINT" \
  "$BACKUP_FILE" 2>&1 && echo "✓ MinIO backup completed" || echo "✗ MinIO backup failed"

exit 0
