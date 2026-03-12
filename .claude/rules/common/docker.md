# Docker Standards

## Build
- Multi-stage builds to minimize image size
- Pin base image versions (never use `latest`)
- `.dockerignore` to exclude unnecessary files
- Non-root user in final stage

## Runtime
- Health checks on every container
- Resource limits (CPU, memory) on all services
- Named volumes for persistent data (never anonymous volumes)
- No database ports exposed to host in production

## Compose
- Use `.env` file for configuration (not committed)
- Explicit `depends_on` with health check conditions
- Restart policy: `unless-stopped` for production
- Separate compose files for dev vs prod (`docker-compose.override.yml`)

## Security
- No `privileged: true` unless absolutely necessary
- Read-only root filesystem where possible
- Drop all capabilities, add only needed ones
- Scan images for vulnerabilities
