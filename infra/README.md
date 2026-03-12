# Infrastructure — Crypto Bot DevOps

This directory contains all infrastructure-as-code for the Crypto Bot project:
- Docker Compose configurations (local + production)
- Ansible playbooks (VPS provisioning + deployment)
- Nginx reverse proxy configuration
- Prometheus monitoring and alert rules
- Grafana dashboards and provisioning
- Utility scripts (health checks, backups, rollback)

## Directory Structure

```
infra/
├── README.md                          # This file
├── scripts/                           # Utility bash scripts
│   ├── healthcheck.sh                # Health check all services
│   ├── backup-db.sh                  # Database backup
│   ├── backup-minio.sh               # MinIO backup
│   └── rollback.sh                   # Rollback deployment
├── ansible/                          # Infrastructure-as-Code
│   ├── inventories/                  # Host inventories
│   │   └── production.ini.example     # Example production inventory
│   ├── group_vars/
│   │   └── vps.yml                   # Group variables for VPS
│   ├── templates/
│   │   └── jail.local.j2             # Fail2Ban configuration
│   └── playbooks/
│       ├── provision.yml             # One-time VPS setup
│       ├── deploy.yml                # Application deployment
│       ├── backup.yml                # Backup automation
│       ├── ssl.yml                   # SSL/TLS setup
│       └── setup-https.yml           # HTTPS redirection
├── nginx/
│   └── nginx.conf                    # Reverse proxy + rate limiting + security headers
├── prometheus/
│   ├── prometheus.yml                # Scrape targets + retention policy
│   └── alert_rules.yml               # Alert conditions
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml         # Prometheus data source
    │   ├── dashboards.yml             # Dashboard provisioning config
    │   ├── alerts.yml                 # Alert notification config
    │   └── alertmanager.yml           # Alertmanager config (optional)
    └── dashboards/
        ├── api_overview.json          # API metrics dashboard
        ├── database.json              # Database performance dashboard
        ├── business.json              # Business metrics dashboard
        └── system.json                # System resources dashboard
```

## Quick Start

### Local Development

```bash
# Copy environment template and edit with passwords
cp ../.env.example ../.env
nano ../.env

# Start all services
cd ..
docker-compose up -d

# Verify health
./infra/scripts/healthcheck.sh

# View logs
docker-compose logs -f api
```

### Production Deployment

```bash
# 1. Setup VPS (one-time)
cp infra/ansible/inventories/production.ini.example \
   infra/ansible/inventories/production.ini
nano infra/ansible/inventories/production.ini

# Provision VPS
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml

# 2. Setup .env on VPS
ssh deploy@your-vps.com
cd /opt/crypto-bot
cp .env.example .env
nano .env  # Edit with strong passwords

# 3. Deploy application
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml

# 4. Verify deployment
ssh deploy@your-vps.com
cd /opt/crypto-bot
./infra/scripts/healthcheck.sh
```

## Key Features

### CI/CD Pipelines

Two GitHub Actions workflows:

1. **tests.yml** (on every push/PR)
   - Lint with ruff
   - Type check with mypy
   - Test with pytest (80% coverage gate)
   - Docker build validation

2. **deploy.yml** (on push to main)
   - Build all 5 Docker images
   - Push to Docker Registry
   - Deploy to VPS via Ansible
   - Post-deploy health checks
   - Slack notifications (optional)

### Docker Compose

- 13 services (API, Frontend, ETL, ML, DB, Storage, Monitoring)
- Health checks on every service
- Resource limits (prevent OOM)
- Named volumes (data persistence)
- Development overrides (hot-reload, debug logging)

### Security

- UFW firewall (block all, allow 22/80/443)
- Fail2Ban (brute-force protection)
- HTTPS with Let's Encrypt
- Security headers (CSP, X-Frame-Options, HSTS)
- Rate limiting (API 30 req/s, Auth 5 req/min)
- Non-root user (deploy) with sudo/docker groups

### Monitoring

- Prometheus (15-day retention, 30s scrape interval)
- Grafana (4 dashboards + alerts)
- Alert rules for critical conditions
- Exporters: postgres, nginx, node (optional), cadvisor (optional)

### High Availability

- Health checks detect failures
- `restart: unless-stopped` survives reboots
- Database backups (daily, 30-day retention)
- Pre-deployment backups
- Rollback script for quick recovery

## Common Tasks

### View Logs

```bash
# API logs
docker-compose logs -f api

# All services
docker-compose logs -f

# Specific service (10 lines)
docker-compose logs --tail=10 api
```

### Health Check

```bash
./infra/scripts/healthcheck.sh
```

### Backup Database

```bash
# Manual backup
./infra/scripts/backup-db.sh

# Restore from backup
gunzip < backups/timescaledb_*.sql.gz | \
  docker-compose exec -T timescaledb psql -U cryptobot
```

### Restart Service

```bash
docker-compose restart api
```

### Scale Service

```bash
# Run 2 instances of api
docker-compose up -d --scale api=2
```

### SSH to VPS

```bash
ssh deploy@your-vps.com
cd /opt/crypto-bot
docker-compose ps
```

### Check Resource Usage

```bash
docker stats
```

### View Metrics

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (user: admin)
- MinIO: http://localhost:9001
- MLflow: http://localhost:5000

## Troubleshooting

### Service won't start

```bash
docker-compose logs <service>
docker-compose ps
```

### High memory usage

```bash
docker stats
# Edit memory limit in docker-compose.yml
```

### Database connection error

```bash
docker-compose exec timescaledb pg_isready
echo $DATABASE_URL
```

### SSL certificate issue

```bash
sudo certbot certonly --standalone -d your-domain.com
sudo systemctl reload nginx
```

### Deployment stuck

```bash
# Check GitHub Actions logs
# SSH to VPS and check:
cd /opt/crypto-bot
docker-compose logs api
docker-compose logs nginx
```

## Environment Variables

All required variables documented in `../.env.example`:

- `POSTGRES_*`: Database credentials
- `MINIO_*`: S3-compatible storage credentials
- `API_SECRET_KEY`: JWT signing key
- `GF_SECURITY_ADMIN_PASSWORD`: Grafana admin password
- `COINGECKO_API_KEY`: (optional) CoinGecko API key
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: (optional) LLM providers

## Files Reference

### Docker Compose

- `../docker-compose.yml`: Production configuration
- `../docker-compose.override.yml.example`: Development overrides
- `../docker-compose.override.yml`: Auto-loaded (local only)

### Dockerfiles

- `../src/api/Dockerfile`: FastAPI app
- `../src/frontend/Dockerfile`: Streamlit app
- `../src/etl/Dockerfile`: ETL worker
- `../src/ml/Dockerfile`: ML worker
- `../src/ml/Dockerfile.mlflow`: MLflow tracking server

### GitHub Actions

- `../.github/workflows/tests.yml`: CI pipeline
- `../.github/workflows/deploy.yml`: CD pipeline

## Best Practices

1. **Never commit secrets**: .env is in .gitignore
2. **Use strong passwords**: 16+ chars, mixed case, numbers, symbols
3. **Backup before deploy**: `deploy.yml` does this automatically
4. **Monitor continuously**: Check Grafana dashboards regularly
5. **Test locally first**: `docker-compose up -d` before pushing
6. **Review logs after deploy**: `docker-compose logs`
7. **Keep dependencies updated**: Regular security updates for base images

## Resources

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Ansible Docs](https://docs.ansible.com/)
- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Main Documentation](../docs/05-devops-infra.md)
