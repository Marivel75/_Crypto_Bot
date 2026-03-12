# GitHub Actions Setup

## Overview

This project uses GitHub Actions for automated CI/CD:
1. **Tests** (`.github/workflows/tests.yml`) — runs on every push/PR
2. **Deploy** (`.github/workflows/deploy.yml`) — runs on push to `main` only

---

## Step 1: Configure Repository Secrets

Go to: `https://github.com/YOUR_ORG/roulio-mars/settings/secrets/actions`

### Required Secrets for Production Deployment

#### VPS_HOST
- **Value:** `3.253.52.249`
- **Purpose:** Target VPS IP for deployment

#### VPS_SSH_KEY
- **Value:** Contents of your SSH private key (`~/.ssh/crypto-bot-deploy`)
- **How to get:**
  ```bash
  cat ~/.ssh/crypto-bot-deploy
  # Copy entire output (including BEGIN/END lines)
  ```
- **Purpose:** Ansible SSH authentication to VPS

#### DOCKER_REGISTRY_USERNAME
- **Value:** Your Docker Hub username (or other registry)
- **Purpose:** Authenticate to registry for image push

#### DOCKER_REGISTRY_PASSWORD
- **Value:** Docker Hub access token (NOT your password)
- **How to get:** https://hub.docker.com/settings/security
  - Click "New Access Token"
  - Give it name: "crypto-bot-ci"
  - Copy the token
- **Purpose:** Push Docker images to registry

### Optional Secrets

#### SLACK_WEBHOOK_URL
- **Value:** Slack webhook URL for notifications
- **How to get:** https://api.slack.com/apps → Create New App → Incoming Webhooks
- **Purpose:** Send deployment success/failure notifications to Slack

---

## Step 2: Verify SSH Key Configuration

The deploy workflow uses Ansible, which needs SSH access:

```bash
# On VPS (as root):
ssh root@3.253.52.249

# Verify deploy user has SSH key:
cat /home/deploy/.ssh/authorized_keys

# Should contain your public key (from provision playbook)
```

---

## Step 3: Test CI/CD Pipeline

### Create a test commit to trigger CI

```bash
git checkout main
git pull origin main

# Make a trivial change:
echo "# Test deployment" >> README.md
git add README.md
git commit -m "test: trigger CI/CD pipeline"
git push origin main
```

### Monitor the pipeline

- Go to: `https://github.com/YOUR_ORG/roulio-mars/actions`
- Wait for all jobs to complete (30-40 minutes)
- Check for failures in logs

### Expected workflow steps

1. **Checkout code** — 30 sec
2. **Lint (ruff)** — 3 min
3. **Type check (mypy)** — 5 min
4. **Test (pytest)** — 10 min
5. **Build Docker images** — 15 min
6. **Deploy to VPS (Ansible)** — 5 min
7. **Health check** — 1 min
8. **Slack notification** — 30 sec (if configured)

---

## Step 4: Troubleshooting Deployment

### SSH Connection Failed

**Error message:**
```
fatal: [3.253.52.249]: UNREACHABLE! => {
    "changed": false,
    "msg": "Failed to connect to the host via ssh: Permission denied"
}
```

**Solution:**
1. Verify `VPS_SSH_KEY` is correct (full key with BEGIN/END lines)
2. Verify `VPS_HOST` matches actual VPS IP
3. Check SSH key is added to `~/.ssh/authorized_keys` on VPS:
   ```bash
   ssh root@3.253.52.249
   cat ~/.ssh/authorized_keys
   ```

### Docker Image Push Failed

**Error message:**
```
denied: requested access to the resource is denied
```

**Solution:**
1. Verify `DOCKER_REGISTRY_USERNAME` and `DOCKER_REGISTRY_PASSWORD` are correct
2. Ensure you're using an access token, NOT your Docker password
3. Verify token has push permissions

### Health Check Timeout

**Error message:**
```
Health check failed after 15 attempts
```

**Causes:**
- Containers still starting up (normal for first deploy)
- Database migration taking longer than expected
- Network connectivity issue

**Solution:**
- Wait 2-3 minutes and check manually:
  ```bash
  ssh deploy@3.253.52.249 docker-compose ps
  ssh deploy@3.253.52.249 docker-compose logs api
  ```

---

## Step 5: Monitor Deployments

### GitHub Actions UI

- Current status: `https://github.com/YOUR_ORG/roulio-mars/actions`
- Latest run: Shows estimated time remaining, logs, duration
- Workflow history: All previous deployments

### Real-time Monitoring

Once deployed, monitor from your VPS:

```bash
ssh deploy@3.253.52.249

# Watch service health:
watch -n 5 'docker-compose ps'

# Tail API logs:
docker-compose logs -f api

# Run health check:
bash /opt/crypto-bot/infra/scripts/healthcheck.sh
```

### Slack Notifications

If `SLACK_WEBHOOK_URL` is configured, you'll receive messages:
- ✅ Deployment successful
- ❌ Deployment failed

---

## Step 6: Manual Deployment (Without GitHub Actions)

If you prefer to deploy without pushing to `main`:

```bash
# From project root:
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml \
  -e "image_tag=latest"
```

---

## Secrets Security Best Practices

- ✅ Use GitHub-generated SSH keys, not personal keys
- ✅ Rotate secrets if compromised
- ✅ Use least-privilege Docker tokens (push only)
- ✅ Never commit `.env` or secrets to git
- ✅ Audit secret access: Settings → Security → Audit log

---

## Advanced: Custom Deployment Parameters

If you need to deploy a specific image tag (not latest):

```bash
# Via GitHub Actions (edit workflow and uncomment):
git push origin main

# Via Ansible (manual):
ansible-playbook \
  -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/deploy.yml \
  -e "image_tag=v1.2.3"
```

---

**Next step:** Run your first test deployment. See `QUICKSTART_DEPLOYMENT.md`.

