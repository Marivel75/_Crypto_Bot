# Crypto Bot — Infrastructure Ready for Production

**Status:** COMPLETE ✅

This document summarizes the production-ready infrastructure for the Crypto Bot project.

---

## What's Implemented

### 1. CI/CD Pipeline (GitHub Actions)

**Files:**
- `.github/workflows/tests.yml` — Lint, type check, test on every push/PR
- `.github/workflows/deploy.yml` — Build and deploy to VPS on push to main

**Features:**
- Linting with ruff (8 rule sets)
- Type checking with mypy (strict mode)
- Tests with pytest (80% coverage gate)
- Docker image builds for 5 services (API, Frontend, ETL, ML, MLflow)
- Ansible deployment to VPS
- Health check verification (15-minute timeout)
- Slack notifications (optional)

**Status:** Ready. Requires GitHub secrets setup.

### 2. Docker Compose Orchestration

**Files:**
- `docker-compose.yml` — 13 production services
- `docker-compose.override.yml.example` — Local dev overrides (hot reload)

**Services:**
- **Data:** TimescaleDB (PostgreSQL + hypertables)
- **Storage:** MinIO (S3-compatible object storage)
- **ML/Tracking:** MLflow (experiment tracking)
- **Application:** API (FastAPI), Frontend (Streamlit)
- **Workers:** ETL worker, ML worker
- **Proxy:** Nginx (reverse proxy + SSL)
- **Monitoring:** Prometheus, Grafana
- **Exporters:** PostgreSQL exporter, Nginx exporter

**Features:**
- Health checks on all services
- Resource limits (CPU, memory)
- Named volumes (persistence)
- Internal networks (frontend, backend)
- Proper dependencies with health conditions

**Status:** Ready. Deploy with `docker-compose up -d`.

### 3. Ansible Infrastructure-as-Code

**Files:**
- `infra/ansible/playbooks/provision.yml` — VPS base setup
- `infra/ansible/playbooks/deploy.yml` — Application deployment
- `infra/ansible/playbooks/backup.yml` — Database backups
- `infra/ansible/inventories/production.ini` — VPS configuration (FOR YOUR IP)
- `infra/ansible/group_vars/vps.yml` — Ansible variables

**Provision Playbook** (one-time):
- Install Docker, Docker Compose, Nginx
- Setup UFW firewall (allow 22, 80, 443)
- Install Fail2Ban (brute-force protection)
- Create deploy user with SSH access
- Setup swap, timezone, log rotation

**Deploy Playbook** (per deployment):
- Sync code to VPS (excludes git, cache, data)
- Backup database (pre-deploy safety)
- Run docker-compose up
- Verify health checks
- Cleanup old backups (>30 days)

**Status:** Ready. Requires inventory configuration.

### 4. Monitoring & Alerting

**Files:**
- `infra/prometheus/prometheus.yml` — Metrics scrape configuration
- `infra/prometheus/alert_rules.yml` — Alert conditions (13+ rules)
- `infra/grafana/provisioning/` — Dashboard provisioning

**Monitored Metrics:**
- API: latency, error rate, requests/sec
- Database: connections, queries, cache hit ratio
- Containers: CPU, memory, disk usage
- Nginx: requests, upstream latency
- Services: health status, uptime

**Alert Rules:**
- API down (2+ min unavailable)
- Database down
- Nginx down
- High latency (>1s)
- High error rate (>5%)
- High CPU (>80%)
- High memory (>85%)
- Data staleness (ETL not running)
- No recent signals (ML not generating)

**Status:** Ready. Access Grafana at `http://localhost:3000` or `https://your-domain.com:3000`.

### 5. Health Checking & Operational Scripts

**Files:**
- `infra/scripts/healthcheck.sh` — Service availability check
- `infra/scripts/backup-db.sh` — Database backup with retention
- `infra/scripts/rollback.sh` — Rollback to previous deployment

**Features:**
- HTTP health checks (API, Frontend, Nginx, etc.)
- Database connectivity check (pg_isready)
- MinIO S3 health check
- Docker container status verification
- Automated pre-deployment backup
- Automatic cleanup of old backups
- Safe rollback with confirmation

**Status:** Ready. Can be run manually or via cron.

### 6. Configuration Management

**Files:**
- `.env.example` — Environment variable template
- `infra/nginx/nginx.conf` — Nginx configuration
  - Rate limiting (30 req/s API, 5 req/min auth)
  - Security headers (HSTS, CSP, X-Frame-Options)
  - Reverse proxy (API + Frontend)
  - SSL termination (Let's Encrypt)
  - Gzip compression

**Status:** Ready. Copy to `.env` and configure passwords.

---

## VPS Target: 3.253.52.249

### What You Need to Do

#### 1. SSH Key Setup (5 minutes)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/crypto-bot-deploy -N ""
ssh-copy-id -i ~/.ssh/crypto-bot-deploy.pub root@3.253.52.249
```

#### 2. Configure Ansible Inventory (5 minutes)

Edit `infra/ansible/inventories/production.ini`:
```ini
[vps]
cryptobot-prod ansible_host=3.253.52.249 ansible_user=root

[vps:vars]
domain_name=YOUR_DOMAIN
letsencrypt_email=YOUR_EMAIL
ansible_ssh_private_key_file=~/.ssh/crypto-bot-deploy
```

#### 3. Provision VPS (15-20 minutes)

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml
```

Installs Docker, Nginx, Firewall, Fail2Ban, creates deploy user.

#### 4. Configure Environment (5 minutes)

```bash
ssh deploy@3.253.52.249
cd /opt/crypto-bot
cp .env.example .env
nano .env  # Edit POSTGRES_PASSWORD, MINIO_PASSWORD, etc.
exit
```

#### 5. Deploy Application (5-10 minutes)

```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml
```

Or push to main for GitHub Actions deployment.

#### 6. Setup Domain & SSL (10 minutes)

1. Point your domain to 3.253.52.249 (DNS A record)
2. Wait for DNS propagation (5-30 minutes)
3. Run certbot on VPS:
```bash
ssh deploy@3.253.52.249
sudo certbot certonly --standalone -d your-domain.com -m your-email@example.com --agree-tos
```

#### 7. Configure GitHub Actions (10 minutes)

Set these secrets in repo settings:
- `VPS_HOST`: 3.253.52.249
- `VPS_SSH_KEY`: (contents of ~/.ssh/crypto-bot-deploy)
- `DOCKER_REGISTRY_USERNAME`: your-docker-username
- `DOCKER_REGISTRY_PASSWORD`: your-docker-token

### Total Setup Time: ~60-90 minutes

---

## Documentation

**For detailed instructions, see:**

1. **Quick Start** — `QUICKSTART_DEPLOYMENT.md`
   - 5 phases, 30-minute walkthrough
   - Most common commands in table format

2. **Full VPS Deployment Guide** — `VPS_DEPLOYMENT_GUIDE.md`
   - Detailed phase-by-phase instructions
   - Troubleshooting section
   - Maintenance schedules
   - Rollback procedures

3. **GitHub Actions Setup** — `GITHUB_ACTIONS_SETUP.md`
   - How to configure secrets
   - How to troubleshoot deployment failures
   - Manual deployment option

4. **Infrastructure Reference** — `docs/05-devops-infra.md`
   - 11 comprehensive sections
   - Architecture diagrams
   - All playbook documentation
   - Advanced topics

5. **Setup Guide** — `SETUP.md`
   - Zero-to-production walkthrough
   - Local dev setup
   - Production VPS setup
   - Security checklist

6. **Infrastructure README** — `infra/README.md`
   - Directory structure reference
   - Quick start guide
   - Common tasks
   - Troubleshooting

---

## Security Checklist

Before going live, verify:

- [ ] SSH key-based authentication (no password login)
- [ ] UFW firewall enabled (22, 80, 443 only)
- [ ] Fail2Ban running
- [ ] `.env` file with strong passwords (16+ chars)
- [ ] SSL certificate installed
- [ ] Health checks passing
- [ ] Database backups verified
- [ ] Grafana admin password changed
- [ ] MinIO credentials changed from default
- [ ] GitHub Actions secrets configured
- [ ] Rate limiting enabled on API
- [ ] Nginx security headers configured

---

## Deployment Flow

### Manual Deployment

```
Code push → Lint ✓ → Type check ✓ → Tests ✓ → 
Docker build → Push to registry → 
Ansible SSH to VPS → Backup DB → 
Pull images → docker-compose up → 
Health check ✓ → Success!
```

### Automated Deployment

```
Push to main branch →
GitHub Actions trigger →
(same as manual flow above) →
Slack notification
```

---

## Access Points (After Deployment)

| Service | URL | Auth |
|---------|-----|------|
| Frontend | `https://your-domain.com` | Public |
| API Docs | `https://your-domain.com/api/docs` | Public |
| API Health | `https://your-domain.com/api/v1/health` | Public |
| Grafana | `https://your-domain.com:3000` | admin/PASSWORD |
| MinIO | `https://your-domain.com:9001` | ROOT_USER/PASSWORD |
| Prometheus | `http://localhost:9090` (internal) | Public |

---

## Monitoring

**Real-time:**
- Grafana dashboards (4 pre-built)
- Prometheus metrics
- Nginx access logs
- Docker health checks

**Alerts:**
- Slack webhook (if configured)
- Grafana alert rules (13+)
- Email (optional, via Alertmanager)

**Logs:**
```bash
docker-compose logs -f SERVICE_NAME
tail -f nginx-logs-data/access.log
tail -f nginx-logs-data/error.log
```

---

## Support

**Quick reference:**
- `.github/workflows/tests.yml` — CI pipeline
- `.github/workflows/deploy.yml` — Deployment pipeline
- `infra/ansible/playbooks/` — Infrastructure automation
- `infra/scripts/` — Operational tools
- `docker-compose.yml` — Service definitions
- `infra/nginx/` — Reverse proxy config
- `infra/prometheus/` — Monitoring config

**Documentation:**
- `SETUP.md` — Zero to production
- `VPS_DEPLOYMENT_GUIDE.md` — Detailed walkthrough
- `QUICKSTART_DEPLOYMENT.md` — Quick reference
- `GITHUB_ACTIONS_SETUP.md` — CI/CD configuration
- `docs/05-devops-infra.md` — Comprehensive reference
- `infra/README.md` — Infrastructure directory

---

## What's NOT Included

- Kubernetes (Docker Compose for V1)
- Paid monitoring services
- Managed database (use local TimescaleDB)
- CDN (can add CloudFlare later)
- Email service (use SendGrid or similar)
- S3 backups (backups stored locally in MinIO)

---

## Next Steps

1. ✅ Review this checklist
2. ✅ Setup SSH key
3. ✅ Configure Ansible inventory
4. ✅ Run provision playbook
5. ✅ Configure .env file
6. ✅ Run deploy playbook
7. ✅ Setup domain and SSL
8. ✅ Configure GitHub Actions secrets
9. ✅ Test CI/CD pipeline
10. ✅ Monitor Grafana dashboard

**Estimated time:** 60-90 minutes

---

**Last updated:** 2026-03-12
**Status:** Production Ready

