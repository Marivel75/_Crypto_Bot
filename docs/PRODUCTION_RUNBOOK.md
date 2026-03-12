# Production Runbook — Crypto Bot

**Version**: 2.0  
**Last Updated**: 2026-03-12  
**Owner**: DevOps Team  
**Audience**: On-call engineers, incident responders

## Table of Contents
1. [Contacts & Escalation](#contacts--escalation)
2. [Service Overview](#service-overview)
3. [Monitoring & Alerts](#monitoring--alerts)
4. [Common Issues & Resolution](#common-issues--resolution)
5. [Incident Response](#incident-response)
6. [Backup & Recovery](#backup--recovery)
7. [Deployment & Rollback](#deployment--rollback)

---

## Contacts & Escalation

### On-Call Rotation
- **Primary**: DevOps Lead (Slack: #on-call)
- **Secondary**: Backend Team Lead
- **Escalation**: CTO (critical security/data issues)

### External Resources
- **Let's Encrypt Support**: https://letsencrypt.org/contact/
- **Docker Support**: https://www.docker.com/support
- **Hosting Provider**: Contact info in vault (ask CTO)

### Critical Contacts
- **Security Incident**: security@example.com
- **Data Loss**: data-team@example.com
- **Stakeholders**: product@example.com

---

## Service Overview

### Architecture
```
Client (HTTPS) → Nginx (Reverse Proxy) → FastAPI (8000) + Streamlit (8501)
                                      → TimescaleDB (5432)
                                      → MinIO (9000)
                                      → MLflow (5000)
```

### Services & Health Checks
| Service | Port | Health Check | Timeout |
|---------|------|--------------|---------|
| Nginx | 80/443 | `GET /health` | 10s |
| API | 8000 | `GET /health` | 10s |
| Frontend | 8501 | `GET /_stcore/health` | 10s |
| TimescaleDB | 5432 | `pg_isready` | 5s |
| MinIO | 9000 | `GET /minio/health/live` | 10s |
| MLflow | 5000 | `GET /` | 10s |
| ETL Worker | — | Python import check | 5s |
| ML Worker | — | Python import check | 10s |

### Critical Endpoints
- **Health**: `https://crypto-bot.example.com/health`
- **API Docs**: `https://crypto-bot.example.com/api/docs`
- **Frontend**: `https://crypto-bot.example.com/`
- **Monitoring**: `https://crypto-bot.example.com/grafana` (internal)
- **Metrics**: `https://crypto-bot.example.com:9090/prometheus` (internal)

### Data Persistence
| Service | Volume | Backup Frequency | Retention |
|---------|--------|------------------|-----------|
| TimescaleDB | `timescaledb-data` | Daily (pg_dump) | 30 days |
| MinIO | `minio-data` | Daily (s3 mirror) | 30 days |
| Prometheus | `prometheus-data` | Not backed up | 15 days |
| Grafana | `grafana-data` | Manual (settings) | N/A |

---

## Monitoring & Alerts

### Dashboard Access
- **Grafana**: `http://localhost:3000` (user: `admin`)
- **Prometheus**: `http://localhost:9090`
- **MLflow**: `http://localhost:5000`
- **MinIO Console**: `http://localhost:9001`

### Critical Metrics to Monitor
1. **API Response Time**: `histogram_quantile(0.95, rate(http_request_duration_seconds[5m]))`
   - Alert if > 2s (P95)
   
2. **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
   - Alert if > 0.1% (1 per 1000 requests)

3. **Database Connection Pool**: `pg_stat_activity_count`
   - Alert if >= 90% of max_connections
   
4. **Disk Usage**: `node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1`
   - Alert if < 10% free (critical at < 5%)

5. **Memory Usage**: `container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8`
   - Alert if > 80% of limit

6. **Certificate Expiration**: Days until expiry
   - Alert 30 days before expiration
   - Critical alert 7 days before

### Log Locations
- **Application Logs**: `docker compose logs --follow [service]`
- **Nginx Access**: `docker compose exec nginx cat /var/log/nginx/access.log`
- **Let's Encrypt**: `/var/log/letsencrypt/letsencrypt.log`
- **Systemd**: `journalctl -u certbot-renew.service`

---

## Common Issues & Resolution

### API Service Down

**Symptoms**: `curl https://crypto-bot.example.com/health` returns error

**Steps**:
1. Check service status: `docker compose ps api`
2. View logs: `docker compose logs --tail=50 api`
3. Check dependencies (DB, MinIO): `docker compose ps`
4. Restart service: `docker compose restart api`
5. If issue persists: run full rollback (see [Rollback](#rollback))

### Database Connection Issues

**Symptoms**: API logs show "connection timeout" or "too many connections"

**Steps**:
1. Check database health: `docker compose exec timescaledb pg_isready`
2. List active connections: `docker compose exec timescaledb psql -U cryptobot -c "SELECT count(*) FROM pg_stat_activity;"`
3. Kill idle connections (if needed):
   ```bash
   docker compose exec timescaledb psql -U cryptobot -c "
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE usename = 'cryptobot' AND state = 'idle' AND query_start < now() - interval '1 hour';
   "
   ```
4. Restart database service: `docker compose restart timescaledb`

### Certificate Expiration

**Symptoms**: Browser shows "certificate expired" or "untrusted certificate"

**Steps**:
1. Check current certificate: `openssl x509 -in /etc/letsencrypt/live/crypto-bot.example.com/fullchain.pem -noout -dates`
2. Manual renewal: `/usr/local/bin/certbot-renew.sh`
3. If renewal fails: `certbot renew --force-renewal --dry-run` (test first)
4. Reload Nginx: `docker compose restart nginx`

### High Memory Usage

**Symptoms**: Container OOMKilled or slow response times

**Steps**:
1. Check memory usage: `docker stats`
2. Identify heavy process: `docker top [container] aux`
3. Check for memory leaks in logs
4. Restart affected service: `docker compose restart [service]`
5. Consider increasing memory limit in docker-compose.yml

### Disk Space Critical

**Symptoms**: `Filesystem full` or `No space left on device`

**Steps**:
1. Check disk usage: `df -h`
2. Find large files: `du -sh /backups/* | sort -h`
3. Clean old backups: `find /backups -mtime +30 -delete`
4. Clean Docker volumes: `docker system prune -a`
5. Check MinIO storage: `docker compose exec minio mc du local/`

### Signal Generation Stalled

**Symptoms**: No new signals in database for > 1 hour

**Steps**:
1. Check ETL worker logs: `docker compose logs --tail=100 etl-worker`
2. Check ML worker logs: `docker compose logs --tail=100 ml-worker`
3. Verify data in MinIO: `docker compose exec minio mc ls local/datasets/`
4. Check API for recent data: `curl https://crypto-bot.example.com/api/crypto/ohlcv/BTCUSDT?limit=10`
5. Restart both workers: `docker compose restart etl-worker ml-worker`

---

## Incident Response

### Incident Severity Levels

| Level | SLA | Example |
|-------|-----|---------|
| **P1 — Critical** | 15 min response | API down, data loss, security breach |
| **P2 — High** | 1 hour response | Degraded performance, certificate expiring |
| **P3 — Medium** | 4 hour response | Single user error, non-critical feature broken |
| **P4 — Low** | 24 hour response | Documentation issue, minor UX bug |

### P1 Incident Procedure

1. **Page on-call engineer** (Slack, phone call)
2. **Start incident channel**: `#incident-crypto-bot-TIMESTAMP`
3. **Assess impact**: What's affected? How many users?
4. **Declare incident**: P1/P2/P3
5. **Take immediate action**: Restart services, rollback if necessary
6. **Communicate**: Update #incident channel every 15 min
7. **Post-mortem**: After recovery, document root cause and prevention

### RCA Template
```
## Incident Report
**Date**: YYYY-MM-DD HH:MM UTC  
**Duration**: X minutes  
**Impact**: X% of users, Y transactions failed

## Timeline
- HH:MM: Detection (automated alert / user report)
- HH:MM: Investigation started
- HH:MM: Root cause identified: [...]
- HH:MM: Mitigation applied: [...]
- HH:MM: Service recovered
- HH:MM: Monitoring verified

## Root Cause
[Technical explanation]

## Resolution
[What was done to fix it]

## Prevention
[How to prevent recurrence]

## Action Items
- [ ] Increase monitoring for X metric
- [ ] Add test case for Y scenario
- [ ] Update runbook for Z procedure
```

---

## Backup & Recovery

### Database Backup

**Location**: `/backups/pre-deploy-*.sql.gz` (created before every deploy)

**Manual backup**:
```bash
docker compose exec -T timescaledb pg_dump -U cryptobot cryptobot | gzip > /backups/manual-$(date +%s).sql.gz
```

**Restore from backup**:
```bash
zcat /backups/pre-deploy-TIMESTAMP.sql.gz | docker compose exec -T timescaledb psql -U cryptobot cryptobot
```

### MinIO Backup

**Location**: `/backups/minio/` (daily at 02:00 UTC)

**Manual backup**:
```bash
infra/scripts/backup-minio.sh
```

**Restore from backup**:
```bash
infra/scripts/backup-minio.sh --restore-from /backups/minio/minio_backup_YYYYMMDD_HHMMSS
```

### Full Recovery Procedure (Disaster)

```bash
# 1. Provision new VPS with same spec
# 2. Clone git repo
# 3. Restore secrets
cp /path/to/backup/.env .env

# 4. Start services
docker compose up -d

# 5. Restore database
zcat /backups/pre-deploy-LATEST.sql.gz | \
    docker compose exec -T timescaledb psql -U cryptobot cryptobot

# 6. Restore MinIO data
infra/scripts/backup-minio.sh --restore-from /backups/minio/latest/

# 7. Verify health
docker compose ps
curl https://crypto-bot.example.com/health

# 8. Update DNS to point to new IP
# (Update A record in DNS provider)
```

---

## Deployment & Rollback

### Deployment Procedure

1. **Prepare**: Ensure all tests pass in CI/CD
2. **Backup**: Automatic backup created before deploy
3. **Deploy**: Run Ansible playbook
   ```bash
   ansible-playbook -i infra/ansible/inventories/production.ini \
     infra/ansible/playbooks/deploy.yml
   ```
4. **Verify**: Health checks run automatically
5. **Monitor**: Watch logs for 5 minutes: `docker compose logs --follow`

### Rollback Procedure

```bash
# Rollback to latest backup
sudo infra/scripts/rollback.sh

# Rollback to specific backup
sudo infra/scripts/rollback.sh 1234567890
```

**Rollback flow**:
1. Stops all services
2. Restores database from backup
3. Restarts services
4. Runs health checks
5. Confirms success or alerts for manual intervention

### Automated Rollback (if health check fails)

Add to Ansible deploy playbook:
```yaml
- name: Run health checks
  # If any health check fails, trigger rollback
  when: health_check.failed
  block:
    - name: Trigger automatic rollback
      command: /usr/local/bin/rollback.sh latest
      become: yes
```

---

## Maintenance Tasks

### Daily
- [ ] Check alert dashboard (Grafana)
- [ ] Verify certificate renewal (30 days before expiry)
- [ ] Monitor error rates in Prometheus

### Weekly
- [ ] Review incident logs
- [ ] Test database restore procedure (dry-run)
- [ ] Check disk usage growth

### Monthly
- [ ] Full backup test (restore to staging environment)
- [ ] Review and update this runbook
- [ ] Capacity planning (growth trends)

### Quarterly
- [ ] Security audit of production environment
- [ ] Update dependencies (Docker images, Python packages)
- [ ] Disaster recovery drill (simulate major outage)

---

## Appendix: Useful Commands

```bash
# Show all running services
docker compose ps

# View real-time logs
docker compose logs --follow [service]

# Enter database shell
docker compose exec timescaledb psql -U cryptobot

# Execute command in running container
docker compose exec [service] [command]

# Backup database
docker compose exec -T timescaledb pg_dump -U cryptobot cryptobot | gzip > backup.sql.gz

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/crypto-bot.example.com/fullchain.pem -noout -dates

# Monitor system resources
docker stats

# View Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a

# Pull latest images
docker compose pull

# Build local images
docker compose build

# Update and restart service
docker compose up -d --pull always [service]
```

---

**Last Reviewed**: 2026-03-12  
**Next Review**: 2026-04-12  
**Emergency Contacts**: See top of document
