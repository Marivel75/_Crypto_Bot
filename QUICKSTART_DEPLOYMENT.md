# Quick Start — VPS Deployment

**VPS IP:** 3.253.52.249

## Prerequisites

```bash
# Local machine: setup SSH key
ssh-keygen -t ed25519 -f ~/.ssh/crypto-bot-deploy -N ""
ssh-copy-id -i ~/.ssh/crypto-bot-deploy.pub root@3.253.52.249
```

## Phase 1: Provision (5 min + 5-10 min apt upgrade)

**Edit inventory file:**
```bash
# infra/ansible/inventories/production.ini
domain_name=your-domain.com
letsencrypt_email=your-email@example.com
ansible_ssh_private_key_file=~/.ssh/crypto-bot-deploy
```

**Run provisioning:**
```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/provision.yml
```

## Phase 2: Configure Environment

**SSH to VPS:**
```bash
ssh deploy@3.253.52.249
cd /opt/crypto-bot
cp .env.example .env
nano .env  # Edit with strong passwords
exit
```

## Phase 3: Deploy Application (3-5 min)

**Manual deployment:**
```bash
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml
```

**Or push to main branch for automated GitHub Actions deployment.**

## Phase 4: Verify

```bash
# From local machine:
ssh deploy@3.253.52.249

# Inside VPS:
docker-compose ps
bash /opt/crypto-bot/infra/scripts/healthcheck.sh

# Test API:
curl -s http://localhost/api/v1/health | jq .
```

## Phase 5: Setup SSL

**Point domain to 3.253.52.249 in DNS (A record)**

Then run:
```bash
ssh deploy@3.253.52.249
sudo certbot certonly --standalone -d your-domain.com -m your-email@example.com --agree-tos
```

## Automated Deployment (GitHub Actions)

**Set repository secrets:**
- `VPS_HOST`: 3.253.52.249
- `VPS_SSH_KEY`: (contents of ~/.ssh/crypto-bot-deploy)
- `DOCKER_REGISTRY_USERNAME`: your-docker-hub-username
- `DOCKER_REGISTRY_PASSWORD`: your-docker-hub-token

**Push to main:**
```bash
git push origin main
# Monitor: https://github.com/YOUR_ORG/roulio-mars/actions
```

## Common Commands

| Task | Command |
|------|---------|
| View logs | `ssh deploy@3.253.52.249 docker-compose logs -f SERVICE` |
| Restart service | `ssh deploy@3.253.52.249 docker-compose restart SERVICE` |
| Health check | `ssh deploy@3.253.52.249 bash infra/scripts/healthcheck.sh` |
| Manual backup | `ssh deploy@3.253.52.249 docker-compose exec -T timescaledb pg_dump -U cryptobot cryptobot \| gzip > backups/manual-$(date +%s).sql.gz` |
| Restore backup | `ssh deploy@3.253.52.249 gunzip < backups/pre-deploy-TIMESTAMP.sql.gz \| docker-compose exec -T timescaledb psql -U cryptobot` |
| Check disk usage | `ssh deploy@3.253.52.249 df -h` |
| Update containers | `ssh deploy@3.253.52.249 docker-compose pull && docker-compose up -d` |

---

**Full guide:** See `VPS_DEPLOYMENT_GUIDE.md`
**Infrastructure reference:** See `docs/05-devops-infra.md`

