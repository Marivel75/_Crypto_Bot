# Crypto Bot — VPS Deployment Guide

## Overview

This guide walks you through provisioning and deploying the Crypto Bot application to a production VPS at **3.253.52.249**.

**Architecture:**
- VPS runs Docker Compose with 13 microservices (API, Frontend, ETL, ML, Database, Storage, Monitoring)
- Nginx reverse proxy with automatic SSL (Let's Encrypt)
- Automated CI/CD via GitHub Actions
- Ansible playbooks for infrastructure-as-code

---

## Phase 1: VPS Initial Setup (One-Time)

### Step 1.1: Prepare SSH Access

You have a `.pem` file for SSH access. Convert it to OpenSSH format if needed:

```bash
# If your .pem file is in RSA format:
ssh-keygen -p -N "" -m pem -f your-vps-key.pem

# Recommended: create ed25519 key for Ansible
ssh-keygen -t ed25519 -f ~/.ssh/crypto-bot-deploy -N ""

# Copy public key to VPS (as root initially):
ssh-copy-id -i ~/.ssh/crypto-bot-deploy.pub -o "IdentitiesOnly=yes" root@3.253.52.249
```

### Step 1.2: Configure Ansible Inventory

Edit `infra/ansible/inventories/production.ini`:

```bash
# Replace these with your actual values:
domain_name=your-domain.com          # e.g., crypto-bot.example.com
letsencrypt_email=your-email@example.com
ansible_ssh_private_key_file=~/.ssh/crypto-bot-deploy
```

### Step 1.3: Provision VPS (Docker, Nginx, Firewall, Fail2Ban)

This installs all base dependencies and security hardening:

```bash
# From project root:
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml \
  -e "domain_name=your-domain.com" \
  -e "letsencrypt_email=your-email@example.com"
```

**What this does:**
- Updates OS packages
- Creates `deploy` user with SSH key
- Installs Docker + Docker Compose
- Sets up UFW firewall (allows 22, 80, 443)
- Installs Fail2Ban (blocks brute-force SSH attempts)
- Installs Nginx + Certbot
- Creates `/opt/crypto-bot` directory

**Duration:** ~5-10 minutes (mostly waiting for `apt upgrade`)

### Step 1.4: Prepare `.env` File on VPS

SSH to the VPS as `deploy` user:

```bash
ssh deploy@3.253.52.249
cd /opt/crypto-bot
cp .env.example .env
nano .env  # or your favorite editor
```

**Required values (use STRONG passwords):**
- `POSTGRES_PASSWORD` (min 16 chars, mixed case, numbers, symbols)
- `MINIO_ROOT_PASSWORD` (min 16 chars)
- `API_SECRET_KEY` (32+ random chars for JWT)
- `GF_SECURITY_ADMIN_PASSWORD` (Grafana UI password)
- `COINGECKO_API_KEY` (optional, leave blank to use free API)

**Example:**
```bash
POSTGRES_PASSWORD=xK9mL2#pQ5@vW8nR
MINIO_ROOT_PASSWORD=mJ7$hB3&wD6!tY4
API_SECRET_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789
GF_SECURITY_ADMIN_PASSWORD=aZ9$mK2#vL5@pQ8
```

Save and exit. **Never commit `.env` to git.**

---

## Phase 2: Application Deployment

### Step 2.1: Configure GitHub Secrets

For automated CI/CD, set these secrets in GitHub repository settings:
`https://github.com/YOUR_ORG/roulio-mars/settings/secrets/actions`

Required:
- `VPS_HOST`: `3.253.52.249`
- `VPS_SSH_KEY`: Contents of `~/.ssh/crypto-bot-deploy` (private key)
- `DOCKER_REGISTRY_USERNAME`: Docker Hub username (if pushing images)
- `DOCKER_REGISTRY_PASSWORD`: Docker Hub access token (not password!)

Optional:
- `SLACK_WEBHOOK_URL`: For deployment notifications

### Step 2.2: Deploy via Ansible (Manual)

If you want to deploy without GitHub Actions:

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml \
  -e "image_tag=latest"
```

**What this does:**
- Syncs code to VPS (excludes .git, __pycache__, .env, data volumes)
- Backs up current database
- Runs `docker-compose up -d`
- Verifies all containers are healthy
- Cleans up old backups (>30 days)

**Duration:** ~3-5 minutes

### Step 2.3: Verify Deployment

SSH to VPS and check services:

```bash
ssh deploy@3.253.52.249

# View running containers:
docker-compose ps

# Check logs:
docker-compose logs -f api
docker-compose logs -f frontend

# Run health check script:
bash /opt/crypto-bot/infra/scripts/healthcheck.sh
```

---

## Phase 3: Domain & SSL Setup

### Step 3.1: Point Your Domain to VPS

In your domain registrar's DNS settings, add an A record:
- **Name:** `@` (or subdomain, e.g., `crypto-bot`)
- **Type:** A
- **Value:** `3.253.52.249`
- **TTL:** 3600

Wait for DNS propagation (5-30 minutes).

### Step 3.2: Obtain SSL Certificate

```bash
ssh deploy@3.253.52.249
cd /opt/crypto-bot

# Use certbot to get SSL certificate:
sudo certbot certonly \
  --standalone \
  -d your-domain.com \
  -m your-email@example.com \
  --agree-tos \
  --no-eff-email

# Certificate path: /etc/letsencrypt/live/your-domain.com/
```

### Step 3.3: Configure Nginx

Update `infra/nginx/nginx.conf` with your domain (or use environment variable substitution in the nginx container).

The deployment playbook should already reference the correct certificate path.

---

## Phase 4: Post-Deployment Verification

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | `https://your-domain.com` | N/A (public) |
| **API Docs** | `https://your-domain.com/api/docs` | N/A (public) |
| **Grafana** | `https://your-domain.com:3000` | admin / YOUR_PASSWORD |
| **MinIO Console** | `https://your-domain.com:9001` | MINIO_ROOT_USER / PASSWORD |
| **MLflow** | `https://your-domain.com:5000` | N/A (internal) |

### Health Check

```bash
# From your local machine:
curl -s https://your-domain.com/api/v1/health | jq .

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2026-03-12T..."
# }
```

### Monitoring Dashboard

Open Grafana: `https://your-domain.com:3000`
- Username: `admin`
- Password: Your GF_SECURITY_ADMIN_PASSWORD

Pre-built dashboards:
- Docker Compose Health
- API Performance (latency, errors, requests)
- Database Metrics (connections, queries, cache)
- MinIO Storage Usage

---

## Phase 5: Continuous Deployment via GitHub Actions

### Automated CI/CD Pipeline

When you push to `main` branch:

1. **Lint** — ruff code style check (3 min)
2. **Type Check** — mypy strict type checking (5 min)
3. **Tests** — pytest with 80% coverage gate (10 min)
4. **Build** — Docker images for API, Frontend, ETL, ML, MLflow (15 min)
5. **Deploy** — Ansible playbook to VPS (5 min)
6. **Health Check** — Verify all services are running (1 min)
7. **Slack Notification** — Success/failure notification (optional)

**Total pipeline time:** ~30-40 minutes

### Triggering Deployment

```bash
# Ensure all tests pass locally:
ruff check src/ && ruff format src/ && mypy src/ && pytest tests/ --cov-fail-under=80

# Push to main:
git push origin main

# Monitor deployment:
# GitHub Actions UI: https://github.com/YOUR_ORG/roulio-mars/actions
```

---

## Maintenance Tasks

### Daily
- Monitor health: `curl https://your-domain.com/api/v1/health`
- Check Grafana dashboard for anomalies
- Review ETL logs for data collection errors

### Weekly
- Review backup status: `ls -lh /opt/crypto-bot/backups/`
- Check Grafana alerts
- Test rollback procedure (optional)

### Monthly
- Full backup test: restore to staging environment
- Review SSL certificate expiration (Certbot auto-renews at 30 days)
- Audit firewall rules: `sudo ufw status`
- Update Docker images: `docker-compose pull`

### Manual Backup

```bash
ssh deploy@3.253.52.249
cd /opt/crypto-bot

# Backup database:
docker-compose exec -T timescaledb pg_dump -U cryptobot cryptobot | gzip > backups/manual-$(date +%s).sql.gz

# Backup MinIO data:
docker-compose exec -T minio mc mirror s3/mlflow-artifacts /backups/minio-artifacts
```

---

## Troubleshooting

### Service Not Starting

```bash
# Check logs:
docker-compose logs timescaledb  # or other service
docker-compose ps  # show status

# Restart service:
docker-compose restart api
docker-compose up -d
```

### Health Check Failing

```bash
# Run manual health check:
bash /opt/crypto-bot/infra/scripts/healthcheck.sh

# Check individual service:
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8501/_stcore/health
```

### Out of Disk Space

```bash
# Check usage:
df -h

# Clean up Docker:
docker system prune -a --volumes  # WARNING: removes all unused images/volumes
docker-compose down  # stop services
```

### Database Connection Failures

```bash
# Check database:
docker-compose exec timescaledb psql -U cryptobot -d cryptobot -c "SELECT now();"

# Check .env:
grep DATABASE_URL .env
```

### SSL Certificate Issues

```bash
# Check expiration:
sudo certbot renew --dry-run

# Renew manually:
sudo certbot renew --force-renewal
```

---

## Rollback Procedure

If a deployment fails:

```bash
# SSH to VPS:
ssh deploy@3.253.52.249
cd /opt/crypto-bot

# List recent backups:
ls -lht backups/ | head -5

# Restore database from backup:
gunzip < backups/pre-deploy-TIMESTAMP.sql.gz | \
  docker-compose exec -T timescaledb psql -U cryptobot -d cryptobot

# Restart services:
docker-compose up -d
```

Or use the automated rollback script:

```bash
bash /opt/crypto-bot/infra/scripts/rollback.sh
```

---

## Security Checklist

- [ ] SSH key-based auth enabled, password login disabled
- [ ] UFW firewall configured (allow 22, 80, 443 only)
- [ ] Fail2Ban running and monitoring failed SSH attempts
- [ ] `.env` file with strong passwords (16+ chars)
- [ ] SSL certificates installed and auto-renewing
- [ ] Regular backups tested and verified
- [ ] Grafana admin password changed from default
- [ ] MinIO root user credentials changed from default
- [ ] GitHub Actions secrets configured (VPS_SSH_KEY, VPS_HOST, etc.)
- [ ] Rate limiting enabled on API endpoints

---

## Support & Monitoring

**Real-time Monitoring:**
- Grafana dashboard: `https://your-domain.com:3000`
- Prometheus metrics: `https://your-domain.com:9090`

**Logs:**
- Docker logs: `docker-compose logs -f SERVICE_NAME`
- Nginx access: `cat /opt/crypto-bot/nginx-logs-data/access.log`
- Nginx errors: `cat /opt/crypto-bot/nginx-logs-data/error.log`

**Alerts:**
- Slack notifications (if SLACK_WEBHOOK_URL configured)
- Email (can be added via Grafana or Alertmanager)

---

## Next Steps

1. ✅ Configure DNS A record → your-domain.com
2. ✅ Provision VPS with Ansible
3. ✅ Setup `.env` with strong passwords
4. ✅ Deploy application
5. ✅ Configure SSL certificate
6. ✅ Verify health checks passing
7. ✅ Setup GitHub Actions secrets
8. ✅ Test CI/CD pipeline with a test commit
9. ✅ Monitor Grafana dashboard
10. ✅ Schedule regular backups and health checks

---

**Questions?** Check the infrastructure documentation:
- `docs/05-devops-infra.md` — Comprehensive reference
- `SETUP.md` — Detailed setup walkthrough
- `infra/README.md` — Infrastructure directory guide

