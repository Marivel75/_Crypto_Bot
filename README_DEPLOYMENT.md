# Crypto Bot — Deployment & Infrastructure

**Status:** Production Ready ✅

This is the main entry point for infrastructure, deployment, and operational information.

---

## Quick Start (5 minutes)

Start here if you want to get up and running quickly.

**Before you start:**
- You have VPS at `3.253.52.249`
- You have SSH access (`.pem` file)
- You have a domain name (or will set one up)

**Quick steps:**

```bash
# 1. Setup SSH key
ssh-keygen -t ed25519 -f ~/.ssh/crypto-bot-deploy -N ""
ssh-copy-id -i ~/.ssh/crypto-bot-deploy.pub root@3.253.52.249

# 2. Configure Ansible
cp ANSIBLE_INVENTORY_EXAMPLE.ini infra/ansible/inventories/production.ini
# Edit: domain_name, letsencrypt_email, ansible_ssh_private_key_file

# 3. Provision VPS (Docker, Nginx, Firewall)
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml

# 4. Configure environment
ssh deploy@3.253.52.249
cd /opt/crypto-bot && cp .env.example .env
nano .env  # Edit passwords
exit

# 5. Deploy application
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml

# 6. Verify
ssh deploy@3.253.52.249
docker-compose ps && bash /opt/crypto-bot/infra/scripts/healthcheck.sh
```

**Total time:** 30-50 minutes (mostly waiting for apt upgrade during provision)

---

## Documentation Guide

### For First-Time Setup

1. **INFRASTRUCTURE_READY.md** ← Start here
   - What's implemented (complete overview)
   - Security checklist
   - VPS access points
   - Total setup time estimate

2. **VPS_DEPLOYMENT_GUIDE.md** ← Detailed walkthrough
   - Phase 1: VPS Initial Setup
   - Phase 2: Application Deployment
   - Phase 3: Domain & SSL
   - Phase 4: Post-Deployment Verification
   - Phase 5: Continuous Deployment

3. **QUICKSTART_DEPLOYMENT.md** ← Quick reference
   - Commands in table format
   - Common tasks
   - For experienced users

4. **GITHUB_ACTIONS_SETUP.md** ← CI/CD configuration
   - How to configure secrets
   - Testing the pipeline
   - Troubleshooting

### For Infrastructure Details

5. **docs/05-devops-infra.md** ← Comprehensive reference
   - 11 major sections
   - All playbooks documented
   - Advanced topics

6. **infra/README.md** ← Infrastructure directory
   - Directory structure
   - File organization
   - Common tasks

---

## Key Files

### Deployment Files

| File | Purpose |
|------|---------|
| `.github/workflows/tests.yml` | CI: lint, type check, test |
| `.github/workflows/deploy.yml` | CD: build, push, deploy to VPS |
| `docker-compose.yml` | 13 microservices definition |
| `docker-compose.override.yml.example` | Local dev overrides |

### Infrastructure Files

| File | Purpose |
|------|---------|
| `infra/ansible/playbooks/provision.yml` | VPS base setup (one-time) |
| `infra/ansible/playbooks/deploy.yml` | Application deployment |
| `infra/ansible/playbooks/backup.yml` | Database backup & rotation |
| `infra/ansible/inventories/production.ini.example` | Inventory template |
| `ANSIBLE_INVENTORY_EXAMPLE.ini` | Ready-to-use for 3.253.52.249 |
| `infra/ansible/group_vars/vps.yml` | Ansible variables |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Environment variables template |
| `infra/nginx/nginx.conf` | Nginx configuration |
| `infra/prometheus/prometheus.yml` | Metrics scraping config |
| `infra/prometheus/alert_rules.yml` | Alert conditions (13+ rules) |

### Operational Scripts

| File | Purpose |
|------|---------|
| `infra/scripts/healthcheck.sh` | Service availability check |
| `infra/scripts/backup-db.sh` | Database backup script |
| `infra/scripts/rollback.sh` | Rollback to previous deployment |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub (git push)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GitHub Actions Workflows                            │  │
│  │                                                      │  │
│  │  1. tests.yml   : Lint → Type → Test → Build       │  │
│  │  2. deploy.yml  : Build → Push → Ansible → Health  │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────────┘
                           │ Ansible
                           ↓
┌─────────────────────────────────────────────────────────────┐
│           VPS (3.253.52.249) — Docker Compose              │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │  Frontend   │  │   API       │  │ Nginx (Proxy)    │   │
│  │ (Streamlit) │  │ (FastAPI)   │  │ (SSL/Certs)      │   │
│  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘   │
│         │                │                   │             │
│  ┌──────────────────────────────────────────┘             │
│  │                                                        │
│  ├─ TimescaleDB (PostgreSQL)                            │
│  ├─ MinIO (S3-compatible storage)                       │
│  ├─ MLflow (ML tracking)                               │
│  ├─ ETL Worker (Data collection)                       │
│  ├─ ML Worker (Signal generation)                      │
│  ├─ Prometheus (Metrics)                               │
│  ├─ Grafana (Dashboards)                               │
│  └─ Exporters (PostgreSQL, Nginx)                      │
│                                                        │
│  Monitoring:                                           │
│  - Health checks on all services                       │
│  - Resource limits (CPU, memory)                       │
│  - Named volumes for persistence                       │
│  - Pre-deployment backups                              │
└────────────────────────────────────────────────────────┘
```

---

## Deployment Workflow

### Manual Deployment

```
1. Edit code locally
2. Run quality gates: ruff check && mypy && pytest
3. Commit: git add . && git commit -m "type(scope): description"
4. Push to branch: git push origin your-branch
5. Create PR, get review
6. Merge to main: git merge --squash
7. Push main: git push origin main
   ↓
8. GitHub Actions triggers (tests.yml + deploy.yml)
   - Lint, type check, test
   - Build Docker images
   - Push to registry
   - Ansible SSH to VPS
   - Backup database
   - docker-compose pull && up -d
   - Health check
   - Slack notification
   ↓
9. Deployment complete (30-40 minutes)
```

### Automated Deployment (Recommended)

```
Push to main → GitHub Actions → Deploy to VPS → Slack notification
```

---

## Production Access Points

After deployment, access your services here:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | https://your-domain.com | Public |
| **API Docs** | https://your-domain.com/api/docs | Public |
| **API Health** | https://your-domain.com/api/v1/health | Public |
| **Grafana** | https://your-domain.com:3000 | admin / PASSWORD |
| **MinIO** | https://your-domain.com:9001 | ROOT_USER / PASSWORD |
| **Prometheus** | http://localhost:9090 (internal) | Public |

---

## Common Tasks

### Deploy Code

```bash
# Push to main (automatic)
git push origin main

# Or manual deployment
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml
```

### View Logs

```bash
ssh deploy@3.253.52.249
docker-compose logs -f SERVICE_NAME  # e.g., api, frontend, etl-worker
```

### Health Check

```bash
ssh deploy@3.253.52.249
bash /opt/crypto-bot/infra/scripts/healthcheck.sh
```

### Database Backup

```bash
ssh deploy@3.253.52.249
docker-compose exec -T timescaledb pg_dump -U cryptobot cryptobot | \
  gzip > /opt/crypto-bot/backups/manual-$(date +%s).sql.gz
```

### Restart Service

```bash
ssh deploy@3.253.52.249
docker-compose restart api  # or frontend, etl-worker, etc.
```

### Update Containers

```bash
ssh deploy@3.253.52.249
cd /opt/crypto-bot
docker-compose pull
docker-compose up -d
```

---

## Troubleshooting

### Service Not Starting

Check logs:
```bash
docker-compose logs SERVICE_NAME
docker-compose ps
```

### Health Check Failing

Run manual check:
```bash
bash /opt/crypto-bot/infra/scripts/healthcheck.sh
```

### Out of Disk Space

Clean up:
```bash
docker system prune -a --volumes  # WARNING: destructive
```

### Database Connection Error

Verify configuration:
```bash
grep DATABASE_URL .env
docker-compose exec timescaledb psql -U cryptobot -d cryptobot -c "SELECT now();"
```

---

## Security

Before going live, verify:

- [ ] SSH key-based auth (no passwords)
- [ ] UFW firewall enabled
- [ ] Fail2Ban running
- [ ] Strong passwords in .env (16+ chars)
- [ ] SSL certificate installed
- [ ] Health checks passing
- [ ] Database backups tested
- [ ] Grafana admin password changed
- [ ] MinIO credentials updated
- [ ] GitHub Actions secrets configured
- [ ] Rate limiting enabled
- [ ] Nginx security headers configured

See `INFRASTRUCTURE_READY.md` for full checklist.

---

## File Structure

```
.
├── .github/
│   └── workflows/
│       ├── tests.yml         # CI pipeline
│       └── deploy.yml        # CD pipeline
│
├── docker-compose.yml        # Production services
├── docker-compose.override.yml.example  # Local dev
├── .env.example              # Env variables template
│
├── infra/
│   ├── ansible/
│   │   ├── playbooks/
│   │   │   ├── provision.yml # VPS base setup
│   │   │   ├── deploy.yml    # App deployment
│   │   │   └── backup.yml    # Backups
│   │   ├── inventories/
│   │   │   └── production.ini.example
│   │   └── group_vars/
│   │       └── vps.yml       # Variables
│   │
│   ├── nginx/
│   │   └── nginx.conf        # Reverse proxy
│   │
│   ├── prometheus/
│   │   ├── prometheus.yml    # Scrape config
│   │   └── alert_rules.yml   # Alerts
│   │
│   ├── grafana/
│   │   └── provisioning/     # Dashboards
│   │
│   └── scripts/
│       ├── healthcheck.sh    # Health check
│       ├── backup-db.sh      # Backup
│       └── rollback.sh       # Rollback
│
├── docs/
│   ├── 05-devops-infra.md    # Full reference
│   └── ...
│
├── INFRASTRUCTURE_READY.md   # Overview & checklist
├── VPS_DEPLOYMENT_GUIDE.md   # Detailed walkthrough
├── QUICKSTART_DEPLOYMENT.md  # Quick reference
├── GITHUB_ACTIONS_SETUP.md   # CI/CD config
├── ANSIBLE_INVENTORY_EXAMPLE.ini  # Ready-to-use
└── README_DEPLOYMENT.md      # This file
```

---

## Next Steps

1. Read `INFRASTRUCTURE_READY.md` (5 minutes)
2. Follow `VPS_DEPLOYMENT_GUIDE.md` (60 minutes)
3. Configure GitHub Actions secrets (10 minutes)
4. Test deployment by pushing to main (30 minutes)
5. Monitor Grafana dashboard (ongoing)

**Total time to production:** ~60-90 minutes

---

## Support

**Quick reference:** `QUICKSTART_DEPLOYMENT.md`
**Detailed guide:** `VPS_DEPLOYMENT_GUIDE.md`
**Full reference:** `docs/05-devops-infra.md`
**CI/CD setup:** `GITHUB_ACTIONS_SETUP.md`

---

**Last updated:** 2026-03-12
**Infrastructure Status:** Production Ready

