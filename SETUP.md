# Crypto Bot — Complete Setup Guide

This guide walks you through setting up Crypto Bot from zero to production.

## Table of Contents

1. [Local Development](#local-development)
2. [Production VPS](#production-vps)
3. [GitHub Actions CI/CD](#github-actions-cicd)
4. [Domain & SSL](#domain--ssl)
5. [Monitoring & Alerts](#monitoring--alerts)

---

## Local Development

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose v2+)
- Python 3.11+
- Git
- Text editor (VS Code, Vim, Nano)

### Step 1: Clone Repository

```bash
git clone https://github.com/Marivel75/roulio-mars.git
cd roulio-mars
```

### Step 2: Create Environment File

```bash
cp .env.example .env
```

Open `.env` in your editor and replace `CHANGE_ME` values:

**Critical passwords** (minimum 16 characters, mixed case, numbers, symbols):

```bash
POSTGRES_PASSWORD=YourStrong_Password_123!
MINIO_ROOT_PASSWORD=YourStrong_Password_123!
API_SECRET_KEY=YourRandom32CharSecretKeyForJWT123!
GF_SECURITY_ADMIN_PASSWORD=YourStrong_Password_123!
```

Example strong password: `Crypt0B0t_Secure$2024!Q1`

### Step 3: Start Services

```bash
docker-compose up -d
```

First run takes 5-10 minutes (building images, initializing databases).

Monitor startup:
```bash
docker-compose logs -f
```

Wait for all services to show "healthy":
```bash
docker-compose ps
```

### Step 4: Verify Installation

Run health check:
```bash
./infra/scripts/healthcheck.sh
```

All services should show `[OK]`:
```
[OK] API
[OK] Frontend
[OK] MinIO
[OK] Nginx
[OK] Prometheus
[OK] Grafana
[OK] PostgreSQL/TimescaleDB
...
```

### Step 5: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:8501 | None |
| API | http://localhost:8000 | None (auth via JWT) |
| Grafana | http://localhost:3000 | admin / `GF_SECURITY_ADMIN_PASSWORD` |
| MinIO | http://localhost:9001 | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` |
| MLflow | http://localhost:5000 | None |
| Prometheus | http://localhost:9090 | None |

### Step 6: Test Data Flow

1. Open Frontend: http://localhost:8501
2. You should see the cryptocurrency dashboard
3. ETL worker is collecting OHLCV data in the background
4. ML worker is generating signals (check MLflow for experiments)

### Troubleshooting Local Setup

**Port conflicts**:
```bash
# Check which service uses a port
lsof -i :8000

# Use docker-compose.override.yml to change ports
nano docker-compose.override.yml
```

**Out of memory**:
```bash
# Increase Docker memory in Docker Desktop settings
# Or reduce resource limits in docker-compose.yml
```

**Database connection error**:
```bash
# Wait longer for database to initialize
sleep 30
docker-compose restart timescaledb
```

---

## Production VPS

### Prerequisites

- Ubuntu 22.04 LTS server (2GB+ RAM, 20GB+ disk)
- Root SSH access
- Domain name (for SSL)
- Ansible installed locally: `pip install ansible`

### Step 1: Create Inventory File

```bash
# Copy template
cp infra/ansible/inventories/production.ini.example \
   infra/ansible/inventories/production.ini

# Edit with your VPS details
nano infra/ansible/inventories/production.ini
```

Example:
```ini
[vps]
crypto-bot-prod ansible_host=12.34.56.78 ansible_user=root

[vps:vars]
domain_name=crypto-bot.example.com
letsencrypt_email=admin@example.com
```

### Step 2: Provision VPS (One-Time)

This installs Docker, Nginx, Firewall, and other infrastructure:

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml
```

This takes 5-10 minutes. Watch for `ok` and `changed` tasks.

**What it installs**:
- Docker + Docker Compose
- UFW firewall (allows 22, 80, 443)
- Fail2Ban (brute-force protection)
- Nginx (reverse proxy)
- Certbot (SSL certificates)
- Swap (2GB)
- Deploy user with sudo/docker access

### Step 3: Upload .env to VPS

```bash
# SSH to VPS
ssh deploy@your-vps-ip

# Navigate to app directory
cd /opt/crypto-bot

# Copy and edit .env
cp .env.example .env
nano .env
```

Use the same strong passwords as local setup.

### Step 4: Deploy Application (Option A: Manual)

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  -e "image_tag=v1.0.0" \
  infra/ansible/playbooks/deploy.yml
```

This:
1. Syncs code to VPS
2. Pulls latest Docker images
3. Backs up database
4. Starts services
5. Runs health checks

### Step 4: Deploy Application (Option B: GitHub Actions)

This is automatic after you set up secrets:

```bash
# Just push to main
git push origin main

# Watch deployment: GitHub → Actions → Build & Deploy
```

### Step 5: Setup SSL/HTTPS

```bash
# Configure DNS first (your-domain.com → VPS IP)

# Then run Ansible playbook
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  -e "domain_name=your-domain.com" \
  -e "letsencrypt_email=admin@example.com" \
  infra/ansible/playbooks/ssl.yml
```

Or manual Certbot:
```bash
ssh deploy@your-vps-ip
sudo certbot certonly --standalone \
  -d your-domain.com \
  --email admin@example.com \
  --agree-tos
```

### Step 6: Verify Production Setup

```bash
ssh deploy@your-vps-ip
cd /opt/crypto-bot

# Health check
./infra/scripts/healthcheck.sh

# Check services
docker compose ps

# View API
curl http://localhost:8000/api/v1/health

# Check logs
docker compose logs api
```

### Accessing Production

| Service | URL |
|---------|-----|
| Frontend | https://your-domain.com |
| API | https://your-domain.com/api |
| Grafana | https://your-domain.com:3000 |

---

## GitHub Actions CI/CD

### Prerequisites

- GitHub repository configured
- Docker Hub account
- VPS deployed (for deployment step)

### Step 1: Add GitHub Secrets

Go to: GitHub Repository → Settings → Secrets and variables → Actions

Click "New repository secret" for each:

1. **DOCKER_REGISTRY_USERNAME**
   - Your Docker Hub username

2. **DOCKER_REGISTRY_PASSWORD**
   - Docker Hub access token (NOT your password!)
   - Get at: https://hub.docker.com/settings/security

3. **VPS_HOST**
   - Your VPS hostname or IP address
   - Example: `crypto-bot.example.com` or `12.34.56.78`

4. **VPS_SSH_KEY**
   - Private SSH key for deploy user (OpenSSH format)
   - See "SSH Key Setup" below

5. **SLACK_WEBHOOK_URL** (optional)
   - Slack incoming webhook for notifications

### SSH Key Setup

Generate SSH key on your local machine:

```bash
# Generate key
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""

# Add public key to VPS
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@your-vps-ip

# Copy private key to clipboard
cat ~/.ssh/deploy_key | pbcopy  # macOS
xclip -selection clipboard < ~/.ssh/deploy_key  # Linux

# Paste as GitHub Secret VPS_SSH_KEY
```

### Step 2: Test CI Pipeline

Push to feature branch:

```bash
git checkout -b feature/test
git add .
git commit -m "test: CI pipeline"
git push origin feature/test
```

Create Pull Request on GitHub. CI pipeline runs automatically.

Check: GitHub → Actions → CI Pipeline

Expected: All jobs pass (lint, typecheck, test, build)

### Step 3: Test Deployment

Merge to main:

```bash
git checkout main
git merge feature/test
git push origin main
```

Deployment runs automatically. Check: GitHub → Actions → Build & Deploy

Expected:
1. All CI jobs pass
2. Docker images pushed to Docker Hub
3. Application deployed to VPS
4. Health checks pass

### Troubleshooting CI/CD

**Docker login fails**:
- Verify `DOCKER_REGISTRY_PASSWORD` is an access token, not password
- Regenerate token at https://hub.docker.com/settings/security

**SSH connection fails**:
- Verify `VPS_SSH_KEY` is in OpenSSH format (starts with `-----BEGIN OPENSSH PRIVATE KEY-----`)
- Verify `VPS_HOST` is correct
- Verify deploy user exists on VPS: `ssh deploy@vps "echo ok"`

**Health check timeout**:
- Services may need more time to start
- Increase sleep duration in `.github/workflows/deploy.yml`
- Check VPS logs: `ssh deploy@vps "cd /opt/crypto-bot && docker compose logs api"`

---

## Domain & SSL

### DNS Configuration

Point your domain to VPS IP:

```bash
# Example using Namecheap, GoDaddy, AWS Route 53, etc.
# Create A record:
Type: A
Name: @  (or your-domain.com)
Value: 12.34.56.78  (your VPS IP)

# Wait 10 minutes for DNS propagation
# Verify:
nslookup your-domain.com
```

### SSL Certificate

Get free certificate from Let's Encrypt:

```bash
ssh deploy@your-vps-ip

# Request certificate
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --email admin@example.com \
  --agree-tos

# Certificate location: /etc/letsencrypt/live/your-domain.com/
# Auto-renewal: Certbot handles this via cron
```

### HTTPS Redirect

Nginx is configured to redirect HTTP → HTTPS automatically.

Verify:

```bash
# Should redirect to HTTPS
curl -I http://your-domain.com

# Should work
curl -I https://your-domain.com
```

---

## Monitoring & Alerts

### Grafana Dashboards

Access at: http://your-vps-ip:3000 (or https://your-domain.com:3000)

Default login:
```
User: admin
Password: <GF_SECURITY_ADMIN_PASSWORD from .env>
```

**Change this immediately!**

Included dashboards:
1. **API Overview** — Request rate, latency, errors
2. **Database** — Query performance, connections
3. **Container Resources** — CPU, memory usage
4. **Business Metrics** — Signals generated, backtesting

### Create Custom Dashboard

1. Click "Dashboards" → "New Dashboard"
2. Click "Add panel"
3. Choose Prometheus as data source
4. Write PromQL query:
   ```promql
   rate(http_requests_total[5m])  # Request rate
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))  # P95 latency
   rate(http_requests_total{status=~"5.."}[5m])  # Error rate
   ```
5. Click "Save"

### Alerts

Alert rules configured in `infra/prometheus/alert_rules.yml`

Critical alerts:
- API down for 2+ minutes
- Database down for 1+ minute
- Nginx down for 2+ minutes

Warning alerts:
- P95 latency > 1 second
- 5xx error rate > 5%
- Database connections > 50
- Memory usage > 85%
- CPU usage > 80%

View alerts: Prometheus UI (port 9090) → Alerts

### Slack Notifications (Optional)

Set up Slack webhook:

1. Go to Slack workspace → Settings → Apps & integrations
2. Create incoming webhook
3. Add URL as GitHub Secret `SLACK_WEBHOOK_URL`
4. Deployment notifications sent automatically

---

## Security Checklist

Before going to production:

- [ ] Change Grafana default password
- [ ] Change MinIO default credentials (if using)
- [ ] Update Fail2Ban settings if needed
- [ ] Enable UFW firewall
- [ ] Get SSL certificate via Let's Encrypt
- [ ] Review Nginx security headers
- [ ] Enable rate limiting (already configured)
- [ ] Setup database backups
- [ ] Create SSH keys for Ansible deployments
- [ ] Rotate secrets monthly
- [ ] Monitor Grafana dashboards daily
- [ ] Test backup restore procedure

---

## Common Operations

### View Logs

```bash
# Real-time logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api

# Specific service + follow
docker-compose logs -f --tail=50 api
```

### Restart Service

```bash
docker-compose restart api
```

### Scale Service

```bash
docker-compose up -d --scale api=2
```

### Backup Database

```bash
./infra/scripts/backup-db.sh
```

### Restore Database

```bash
gunzip < backups/timescaledb_*.sql.gz | \
  docker-compose exec -T timescaledb psql -U cryptobot
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose build

# Restart services
docker-compose down
docker-compose up -d

# Health check
./infra/scripts/healthcheck.sh
```

### View Resource Usage

```bash
docker stats
```

---

## Next Steps

1. **Read team documentation**: `docs/0X-*.md` for your team
2. **Set up IDE**: Install Python language server, Docker extension
3. **Run tests locally**: `pytest tests/`
4. **Run linting**: `ruff check src/ && mypy src/`
5. **Create feature branch**: `git checkout -b team/feature-name`
6. **Submit PR**: CI pipeline runs automatically
7. **Monitor deployment**: Watch GitHub Actions → Build & Deploy

---

## Support

- Technical docs: `docs/` directory
- Infrastructure docs: `infra/README.md`
- Main README: `README.md`
- Issues: GitHub → Issues
- Team slack: #crypto-bot

Enjoy building Crypto Bot!
