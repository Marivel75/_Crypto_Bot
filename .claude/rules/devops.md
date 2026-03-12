# DevOps / Infra Rules

## Scope: `infra/`, `docker-compose.yml`, `nginx/`, `.github/`

## Docker
- All services defined in `docker-compose.yml`
- Multi-stage builds for Python images
- Health checks on every service
- Named volumes for persistent data (timescaledb-data, minio-data)
- Resource limits on containers

## Nginx
- Reverse proxy for API and frontend
- HTTPS via Let's Encrypt (certbot)
- Rate limiting on API endpoints
- Static asset caching headers

## CI/CD (GitHub Actions)
- On PR: lint (ruff), type check (mypy), tests (pytest), build (docker)
- On merge to main: build + deploy to VPS
- Secrets via GitHub Secrets (never in workflow files)

## Ansible
- Playbooks in `infra/ansible/playbooks/`
- Inventory in `infra/ansible/inventories/`
- VPS provisioning: Docker, Docker Compose, Nginx, certbot, fail2ban, ufw
- Deploy playbook: pull images, docker-compose up, health check

## Backups
- Daily pg_dump of TimescaleDB to MinIO
- 7-day retention for daily, 4-week for weekly
- Test restore procedure monthly

## Monitoring
- Docker health checks on all services
- Nginx access/error logs
- Application logging to stdout (Docker captures)
- Uptime check on `/api/health`

## DO NOT
- Use Kubernetes (Docker Compose for V1)
- Use paid monitoring services
- Expose database ports to the internet
- Store secrets in Docker images or Ansible playbooks
