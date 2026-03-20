# DevOps / Infra Team Context

You are working as the DevOps/Infra agent for crypto-bot.

## Your Scope

- **Code**: `infra/`, `docker-compose.yml`, `nginx/`, `.github/`
- **Doc**: `docs/05-devops-infra.md`
- **Commit scope**: `infra`
- **Do NOT touch**: `src/` (application code belongs to other teams)

## Infrastructure

```
docker-compose.yml      # All services: timescaledb, minio, mlflow, api, frontend, etl-worker, nginx
nginx/
  nginx.conf            # Reverse proxy, HTTPS, rate limiting
  ssl/                  # Let's Encrypt certificates (gitignored)
infra/
  ansible/
    playbooks/          # provision.yml, deploy.yml, backup.yml
    inventories/        # production.ini, staging.ini
    roles/              # docker, nginx, certbot, fail2ban, ufw
.github/
  workflows/
    ci.yml              # PR: lint, typecheck, test, build
    deploy.yml          # merge to main: build + deploy
```

## Docker Rules

- Multi-stage builds for all Python images (build stage + slim runtime)
- Health checks on EVERY service
- Named volumes for persistent data: `timescaledb-data`, `minio-data`
- Resource limits (cpu/memory) on all containers
- Never expose DB ports to the public internet (internal Docker network only)

## CI/CD (GitHub Actions)

On PR:
1. `ruff check src/`
2. `mypy src/`
3. `pytest tests/ --cov=src --cov-fail-under=80`
4. `docker-compose build`

On merge to main:
1. Build Docker images + tag with git SHA
2. Push to registry
3. Run `ansible-playbook deploy.yml`
4. Health check `GET /api/health`

Secrets: all via GitHub Secrets — never in workflow YAML files.

## Nginx

- Reverse proxy: `/api/` -> FastAPI, `/` -> Streamlit
- HTTPS: Let's Encrypt via certbot (auto-renew cron)
- Rate limiting: 10 req/s on `/api/`, 60 req/min on `/api/auth/`
- Static asset cache headers: `Cache-Control: max-age=3600`
- Gzip compression enabled

## Backups

- Daily `pg_dump` of TimescaleDB to MinIO `backups/` bucket
- Retention: 7 daily, 4 weekly
- Test restore procedure monthly
- MinIO data on a persistent mounted volume

## Monitoring

- Docker health checks on all services
- Nginx access and error logs (mounted to host)
- Application logs to stdout (Docker captures via `docker logs`)
- Uptime check on `GET /api/health` (external ping)

## Workflow

1. Read `docs/05-devops-infra.md` for full infra spec
2. Test changes locally with `docker-compose up --build`
3. Validate Ansible syntax: `ansible-playbook --syntax-check`
4. Deploy to staging first, then production
5. Verify health check passes after deploy
