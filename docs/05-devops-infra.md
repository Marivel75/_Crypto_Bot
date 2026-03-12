# DevOps & Infrastructure — Crypto Bot

## Overview

This document covers deployment, CI/CD, monitoring, and infrastructure management for the Crypto Bot project.

**Stack**: Docker Compose (local), Ansible (VPS provisioning), GitHub Actions (CI/CD), Prometheus + Grafana (monitoring), Nginx (reverse proxy), Let's Encrypt (SSL)

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Compose Architecture](#docker-compose-architecture)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [VPS Provisioning & Deployment](#vps-provisioning--deployment)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [SSL/HTTPS Setup](#ssltls-setup)
7. [Backup & Disaster Recovery](#backup--disaster-recovery)
8. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Python 3.11+
- Git
- SSH key pair (for Ansible)

### Quick Start

```bash
# 1. Clone and setup
git clone <repo> && cd roulio-mars
cp .env.example .env

# 2. Edit .env with strong passwords (minimum 16 chars, mixed case, numbers, symbols)
nano .env

# 3. Start all services
docker-compose up -d

# 4. Verify health
./infra/scripts/healthcheck.sh

# 5. Access services
# API: http://localhost:8000
# Frontend: http://localhost:8501
# Grafana: http://localhost:3000 (user: admin)
# MinIO: http://localhost:9001
# MLflow: http://localhost:5000
```

### Environment Variables

Required variables in `.env`:

```bash
# Database
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=your_strong_password_16_chars_min
POSTGRES_DB=cryptobot
DATABASE_URL=postgresql://cryptobot:...@timescaledb:5432/cryptobot

# MinIO
MINIO_ROOT_USER=your_minio_user
MINIO_ROOT_PASSWORD=your_strong_password_16_chars_min
MINIO_ENDPOINT=http://minio:9000

# API
API_SECRET_KEY=your_random_32_char_secret_for_jwt
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:8501"]
LOG_LEVEL=INFO

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
AWS_ACCESS_KEY_ID=your_minio_user
AWS_SECRET_ACCESS_KEY=your_strong_password_16_chars_min

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=your_strong_password_16_chars_min

# Optional
COINGECKO_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Development Overrides

Local development uses `docker-compose.override.yml` which:
- Exposes all ports to localhost
- Mounts source code for hot-reload
- Sets `LOG_LEVEL=DEBUG`
- Enables node-exporter and cAdvisor

This file is automatically applied by Docker Compose and should not be committed.

---

## Docker Compose Architecture

### Services

```
Frontend Layer:
  - nginx (reverse proxy, SSL termination, rate limiting)
  - frontend (Streamlit @ 8501)

Application Layer:
  - api (FastAPI @ 8000)
  - etl-worker (APScheduler, data collectors)
  - ml-worker (signal generation, backtesting)

Infrastructure Layer:
  - timescaledb (time-series database)
  - minio (S3-compatible object storage)
  - mlflow (experiment tracking)

Monitoring Layer:
  - prometheus (metrics collection)
  - grafana (visualization)
  - postgres-exporter (database metrics)
  - nginx-exporter (reverse proxy metrics)
  - node-exporter (Linux system metrics, optional)
  - cadvisor (container metrics, optional)
```

### Health Checks

Every service has a health check:
- **API**: `GET /api/v1/health` (expects 200)
- **Frontend**: `GET /_stcore/health` (Streamlit health endpoint)
- **Database**: `pg_isready` command
- **MinIO**: `GET /minio/health/live` (expects 200)
- **Nginx**: HTTP GET on internal health endpoint
- **Prometheus**: `GET /-/healthy` (expects 200)
- **Grafana**: `GET /api/health` (expects 200)

### Resource Limits

All services have memory limits to prevent OOM on resource-constrained systems:

```yaml
timescaledb:    1GB
minio:          512MB
mlflow:         512MB
api:            512MB
frontend:       512MB
etl-worker:     1GB
ml-worker:      1GB
prometheus:     512MB
grafana:        256MB
postgres-exporter: 64MB
nginx-exporter: 32MB
```

Adjust these in `docker-compose.yml` if running on high-memory servers.

### Volumes

Named volumes for persistence (never anonymous volumes):

```yaml
timescaledb-data:     PostgreSQL data
minio-data:           S3 objects
prometheus-data:      Time-series metrics
grafana-data:         Dashboard configs
nginx-logs-data:      Access/error logs
```

Volume data persists across container restarts. To reset:

```bash
docker compose down -v  # Remove all volumes
docker compose up -d    # Fresh start
```

---

## CI/CD Pipeline

### Workflows

#### 1. **tests.yml** (Lint → Type Check → Test → Build)

Runs on:
- Every push to `main`, `dev`, `roulio-mars`
- Every PR to `main`, `dev`

Stages:
1. **Lint**: `ruff check` (code style, imports, security)
2. **Typecheck**: `mypy --strict` (type safety)
3. **Test**: `pytest --cov-fail-under=80` (unit + integration tests)
4. **Build**: Docker image build validation (no push)

Artifacts:
- Coverage report (HTML) — uploaded as artifact

Slack notification (optional): On PR failure

#### 2. **deploy.yml** (Build & Push → Deploy)

Runs on:
- Push to `main` branch (after all CI checks pass)

Stages:
1. **Lint & Type Check & Test** (same as tests.yml, re-uses cache)
2. **Build & Push**:
   - API image → `docker.io/username/cryptobot-api:latest` + tag
   - Frontend image → `docker.io/username/cryptobot-frontend:latest` + tag
   - ETL image → `docker.io/username/cryptobot-etl:latest` + tag
   - ML image → `docker.io/username/cryptobot-ml:latest` + tag
   - MLflow image → `docker.io/username/cryptobot-mlflow:latest` + tag
3. **Deploy via Ansible**:
   - SSH to VPS
   - Pull latest images
   - Run `docker compose up -d`
   - Health checks
4. **Post-Deploy Health Check**: Verify API and Frontend respond

Slack notifications (optional): Success + Failure

### Required Secrets

Configure these in GitHub repository settings: `Settings → Secrets and variables → Actions`

```
DOCKER_REGISTRY_USERNAME    Docker Hub username
DOCKER_REGISTRY_PASSWORD    Docker Hub access token (NOT password)
VPS_HOST                    Production VPS hostname/IP
VPS_SSH_KEY                 Private SSH key for deploy user (OpenSSH format)
SLACK_WEBHOOK_URL           (optional) Slack incoming webhook for notifications
```

### Docker Registry Setup

1. Create Docker Hub account
2. Generate access token: https://hub.docker.com/settings/security
3. Add to GitHub Secrets as `DOCKER_REGISTRY_PASSWORD`

**Never use your Docker password** — use an access token!

### SSH Key Setup

```bash
# On your local machine
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@your-vps.com

# Add to GitHub Secrets
cat ~/.ssh/deploy_key | pbcopy  # macOS
xclip -selection clipboard < ~/.ssh/deploy_key  # Linux

# Create GitHub Secret VPS_SSH_KEY with the private key content
```

---

## VPS Provisioning & Deployment

### Prerequisites

- Ubuntu 22.04 LTS (or compatible)
- Root access (or sudo)
- Minimum 2GB RAM, 20GB disk
- Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)

### Step 1: Create Ansible Inventory

```bash
cp infra/ansible/inventories/production.ini.example \
   infra/ansible/inventories/production.ini

# Edit with your VPS details
nano infra/ansible/inventories/production.ini
```

Example:
```ini
[vps]
cryptobot-prod ansible_host=192.168.1.100 ansible_user=root

[vps:vars]
domain_name=crypto-bot.example.com
letsencrypt_email=admin@example.com
```

### Step 2: Provision VPS (one-time)

```bash
# Install Ansible
pip install ansible

# Provision the VPS (installs Docker, UFW, Fail2Ban, etc.)
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml
```

What provision.yml does:
- Updates system packages
- Sets timezone
- Creates swap (2GB default)
- Creates deploy user with sudo/docker groups
- Installs Docker + Docker Compose
- Configures UFW firewall (allows 22, 80, 443)
- Installs Fail2Ban (intrusion prevention)
- Installs Nginx + Certbot
- Creates application directory

### Step 3: Setup .env on VPS

```bash
ssh deploy@your-vps.com

cd /opt/crypto-bot
cp .env.example .env

# Edit with strong passwords
nano .env

# Verify permissions
chmod 600 .env
```

### Step 4: Deploy Application

**Option A: Via GitHub Actions** (automatic on push to main)

```bash
# Just push to main, GitHub Actions handles the rest
git push origin main
# Monitor deployment: GitHub → Actions → Build & Deploy
```

**Option B: Manual Deployment** (via Ansible)

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  -e "docker_username=your_dockerhub_user" \
  -e "image_tag=v1.0.0" \
  infra/ansible/playbooks/deploy.yml
```

### Step 5: Verify Deployment

```bash
# SSH to VPS
ssh deploy@your-vps.com

# Check services
cd /opt/crypto-bot
docker compose ps

# Verify health
./infra/scripts/healthcheck.sh

# Check logs
docker compose logs api
docker compose logs frontend
docker compose logs etl-worker
```

---

## Monitoring & Alerting

### Prometheus

Accessible at `http://localhost:9090` (local) or `http://vps:9090` (production)

Scrapes metrics from:
- **api** (port 8000): FastAPI metrics
- **postgres-exporter** (port 9187): Database metrics
- **nginx-exporter** (port 9113): Nginx metrics
- **mlflow** (port 5000): MLflow metrics (if enabled)
- **node-exporter** (port 9100): Linux system metrics (optional)
- **cadvisor** (port 8080): Docker container metrics (optional)

Configuration: `infra/prometheus/prometheus.yml`

### Grafana

Accessible at `http://localhost:3000` (local) or `http://vps:3000` (production)

Default credentials:
```
User: admin
Password: <value of GF_SECURITY_ADMIN_PASSWORD in .env>
```

**Change the default password immediately on production!**

#### Dashboards

Included dashboards:
1. **API Overview** — Request rate, latency, errors, active connections
2. **Database Performance** — Query latency, connections, cache hit ratio
3. **Container Resources** — CPU, memory, disk I/O per service
4. **Business Metrics** — Signals generated, backtesting results

Add custom dashboards:
1. Grafana UI → Dashboards → New Dashboard
2. Add panels (query Prometheus)
3. Save and add to provisioning YAML

### Alert Rules

Prometheus evaluates alert rules every 30 seconds. Configured in:
`infra/prometheus/alert_rules.yml`

Alert conditions:
- **CRITICAL**: API down, Database down, Nginx down
- **WARNING**: High latency (>1s), High error rate (>5%), Low disk space, High connections
- **INFO**: No recent signals (informational)

View alerts: Prometheus UI → Alerts

### Alertmanager (Optional)

Currently disabled. To enable:

1. Deploy Alertmanager container
2. Configure `infra/prometheus/alertmanager.yml`
3. Configure notification channels (email, Slack, PagerDuty)
4. Update `prometheus.yml` to point to Alertmanager

---

## SSL/TLS Setup

### Option 1: Via Let's Encrypt Certbot (Recommended for Production)

Prerequisites: DNS must resolve your domain to the VPS

```bash
# On VPS
ssh deploy@your-vps.com

cd /opt/crypto-bot

# Run certbot interactive setup
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --email admin@example.com \
  --agree-tos

# Certs stored in: /etc/letsencrypt/live/your-domain.com/

# Update nginx config with your domain
sudo nano /etc/nginx/conf.d/default.conf

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Auto-renewal (certbot does this automatically via cron)
sudo systemctl status certbot.timer
```

### Option 2: Via Ansible Playbook

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  -e "domain_name=your-domain.com" \
  -e "letsencrypt_email=admin@example.com" \
  infra/ansible/playbooks/ssl.yml
```

### Nginx SSL Configuration

Configured in `infra/nginx/nginx.conf`:
- HTTPS redirect (HTTP → HTTPS)
- TLS 1.2 + 1.3
- Strong ciphers
- HSTS headers (max-age=1 year)
- Rate limiting (30 req/s API, 5 req/min auth)
- WebSocket support (for Streamlit)
- Security headers (CSP, X-Frame-Options, etc.)

---

## Backup & Disaster Recovery

### Database Backups

Automated daily at 3 AM (configurable in `group_vars/vps.yml`):

```bash
# Manual backup
docker compose exec -T timescaledb pg_dump -U cryptobot cryptobot | gzip > backup.sql.gz

# Restore from backup
gunzip < backup.sql.gz | docker compose exec -T timescaledb psql -U cryptobot
```

### MinIO Backups

Objects in MinIO persist in named volume `minio-data`. To backup:

```bash
# Backup MinIO data
docker run --rm -v minio-data:/data -v /backups:/backups \
  alpine tar czf /backups/minio-$(date +%Y%m%d).tar.gz -C /data .

# Restore
tar xzf /backups/minio-*.tar.gz -C /var/lib/docker/volumes/minio-data/_data/
```

### Full System Backup

```bash
# Backup everything (volumes, code, configs)
tar czf system-backup-$(date +%Y%m%d).tar.gz \
  /opt/crypto-bot \
  /var/lib/docker/volumes/

# Restore
tar xzf system-backup-*.tar.gz -C /
```

### Disaster Recovery Checklist

1. Provision new VPS with `provision.yml`
2. Copy `.env` file
3. Restore backups:
   - `docker compose exec timescaledb pg_restore < backup.sql`
   - Restore MinIO data
4. Run `docker compose up -d`
5. Verify health with `./infra/scripts/healthcheck.sh`

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs <service_name> -f

# Verify health
docker compose ps
docker inspect <container_name>

# Restart service
docker compose restart <service_name>
```

### High Memory Usage

Check `docker compose ps` and resource limits in `docker-compose.yml`:

```bash
# See per-container memory usage
docker stats

# Increase limit (edit docker-compose.yml)
# deploy:
#   resources:
#     limits:
#       memory: 2G  # increase from 1G
docker compose down && docker compose up -d
```

### Database Connection Issues

```bash
# Check database is healthy
docker compose exec timescaledb pg_isready

# Check credentials in .env
grep DATABASE_URL .env

# Test connection
docker compose exec api psql $DATABASE_URL -c "SELECT 1"

# View database logs
docker compose logs timescaledb
```

### API Returns 500 Error

```bash
# Check API logs
docker compose logs api -f

# Check database connectivity
docker compose logs api | grep -i "database\|connection"

# Verify .env variables
docker compose exec api env | sort
```

### Nginx SSL Certificate Issues

```bash
# Check certificate
openssl x509 -in /etc/letsencrypt/live/domain.com/fullchain.pem -text -noout

# Test SSL
curl -vI https://your-domain.com

# Check nginx config
sudo nginx -t
sudo systemctl reload nginx

# Renew certificate
sudo certbot renew --dry-run
```

### GitHub Actions Deployment Fails

Check the action logs: GitHub → Actions → Build & Deploy → failed run

Common issues:
1. **Docker Registry Auth**: Check `DOCKER_REGISTRY_PASSWORD` is an access token, not password
2. **VPS SSH Key**: Verify `VPS_SSH_KEY` is in OpenSSH format (starts with `-----BEGIN OPENSSH PRIVATE KEY-----`)
3. **Health Check Timeout**: VPS services may need more time to start; increase sleep duration in workflow
4. **.env Missing**: Ensure `.env` exists on VPS before deployment

---

## Scripts Reference

### Health Check Script

```bash
./infra/scripts/healthcheck.sh
```

Checks:
- HTTP services (API, Frontend, Nginx, Prometheus, Grafana, MLflow)
- Database connectivity
- MinIO S3 health
- Docker container status

Exit codes: 0 = all healthy, 1 = failures

### Backup Scripts

```bash
# Database backup
./infra/scripts/backup-db.sh

# MinIO backup
./infra/scripts/backup-minio.sh

# Full backup
./infra/scripts/backup-all.sh
```

### Rollback Script

```bash
./infra/scripts/rollback.sh
```

Rolls back to previous Docker Compose configuration.

---

## Best Practices

### Security

1. **Never commit secrets**: .env is in .gitignore
2. **Use strong passwords**: Min 16 chars, mixed case, numbers, symbols
3. **Rotate secrets regularly**: Change DB password, JWT key quarterly
4. **Firewall**: UFW allows only 22, 80, 443
5. **Fail2Ban**: Blocks brute-force SSH attacks
6. **HTTPS only**: Nginx redirects HTTP → HTTPS
7. **Security headers**: CSP, X-Frame-Options, HSTS configured

### Performance

1. **Resource limits**: Prevent OOM kills; monitor with `docker stats`
2. **Database indexes**: Ensure frequently queried columns are indexed
3. **Caching**: Enable in Prometheus, Grafana, API
4. **Rate limiting**: Nginx limits API to 30 req/s, auth to 5 req/min
5. **Compression**: Gzip enabled for responses >1KB

### Reliability

1. **Health checks**: Every service has a health endpoint
2. **Restart policy**: `unless-stopped` (survives reboots)
3. **Backups**: Daily database backups, 30-day retention
4. **Monitoring**: Prometheus + Grafana for alerting
5. **Logs**: All container logs to stdout (Docker captures)

---

## Further Reading

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
