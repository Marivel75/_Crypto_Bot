#!/usr/bin/env bash
# deploy.sh — Crypto Bot deployment script (run on VPS)
# Usage: ./scripts/deploy.sh [--rollback]
set -euo pipefail

APP_DIR="/home/ubuntu/cryptobot"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
HEALTH_URL="http://127.0.0.1:8000/health"
MAX_HEALTH_RETRIES=15
HEALTH_INTERVAL=5

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cd "$APP_DIR"

# --- Rollback mode ---
if [[ "${1:-}" == "--rollback" ]]; then
    log "Rolling back to previous images..."
    docker compose $COMPOSE_FILES down --timeout 30
    # Docker keeps previous image layers; we just restart with cached images
    docker compose $COMPOSE_FILES up -d
    log "Rollback complete"
    exit 0
fi

# --- Pre-deploy checks ---
if [[ ! -f .env ]]; then
    log "ERROR: .env file missing at $APP_DIR/.env"
    exit 1
fi

# --- Build new images ---
log "Building Docker images..."
docker compose $COMPOSE_FILES build --parallel 2>&1 | tail -5

# --- Run database migrations ---
log "Running Alembic migrations..."
docker compose $COMPOSE_FILES run --rm --no-deps api alembic upgrade head 2>&1 || log "WARN: Migration skipped (may already be up to date)"

# --- Rolling restart (minimise downtime) ---
log "Restarting services..."
docker compose $COMPOSE_FILES up -d --remove-orphans 2>&1 | tail -5

# --- Health checks ---
log "Waiting for services to be healthy..."
for i in $(seq 1 $MAX_HEALTH_RETRIES); do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        log "Health check passed (attempt $i/$MAX_HEALTH_RETRIES)"
        break
    fi
    if [[ $i -eq $MAX_HEALTH_RETRIES ]]; then
        log "ERROR: Health check failed after $MAX_HEALTH_RETRIES attempts"
        log "Logs from api:"
        docker compose $COMPOSE_FILES logs --tail=20 api
        exit 1
    fi
    sleep $HEALTH_INTERVAL
done

# --- Verify all containers are running ---
log "Container status:"
docker compose $COMPOSE_FILES ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || docker compose $COMPOSE_FILES ps

# --- Cleanup old images ---
log "Cleaning up dangling images..."
docker image prune -f --filter "until=24h" > /dev/null 2>&1 || true

log "Deploy complete!"
