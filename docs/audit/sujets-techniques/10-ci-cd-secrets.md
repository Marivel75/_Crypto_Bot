# CI/CD Secrets & GitHub Actions Configuration

**Status**: Phase 3 (Medium priority) — D7 DevOps task  
**Date**: 2026-03-12  
**Category**: Infrastructure — GitHub Actions integration

---

## Overview

This document specifies the GitHub Actions secrets required for automated testing, building, and deploying the Crypto Bot to VPS.

**Key Principle**: All secrets are stored in GitHub Secrets (encrypted at rest), never in workflow files or the codebase.

---

## Required Secrets

### Deployment (VPS Access)

| Secret Name | Value | Rotation | Purpose |
|-------------|-------|----------|---------|
| `VPS_HOST` | `crypto-bot.example.com` | Never | VPS hostname for SSH |
| `VPS_USER` | `deploy` | Never | SSH user account on VPS |
| `VPS_SSH_PRIVATE_KEY` | SSH private key (4096-bit RSA) | Every 1 year | SSH authentication for deployment |
| `VPS_SSH_PASSPHRASE` | Passphrase for SSH key | Every 1 year | (optional, if key is encrypted) |

### Production Environment Variables

| Secret Name | Value | Rotation | Purpose |
|-------------|-------|----------|---------|
| `POSTGRES_PASSWORD_PROD` | Strong password (16+ chars) | Every 90 days | TimescaleDB admin password |
| `MINIO_ROOT_PASSWORD_PROD` | Strong password (16+ chars) | Every 90 days | MinIO S3 admin password |
| `API_SECRET_KEY_PROD` | Random 32+ character string | Every 180 days | JWT signing key |
| `GF_SECURITY_ADMIN_PASSWORD_PROD` | Strong password (16+ chars) | Every 90 days | Grafana admin password |

### External APIs (Optional)

| Secret Name | Value | Rotation | Purpose |
|-------------|-------|----------|---------|
| `COINGECKO_API_KEY_PROD` | CoinGecko paid API key | On breach or quarterly | Market data faster rates |
| `OPENAI_API_KEY_PROD` | OpenAI organization API key | On breach or quarterly | ChatGPT integration |

### Container Registry (DockerHub or GHCR)

| Secret Name | Value | Rotation | Purpose |
|-------------|-------|----------|---------|
| `REGISTRY_USERNAME` | Docker Hub username | Never | Registry access |
| `REGISTRY_PASSWORD` | Docker Hub token | Every 180 days | Registry push auth |

---

## Setup Instructions

### Step 1: Generate SSH Keypair (One-Time)

On your local machine or CI runner:

```bash
# Generate 4096-bit RSA key (no passphrase for CI)
ssh-keygen -t rsa -b 4096 -f cryptobot_deploy -N ""

# View the private key
cat cryptobot_deploy
```

### Step 2: Configure VPS SSH Access

On the VPS (as root or sudoer):

```bash
# Create deploy user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy  # allow docker commands without sudo

# Add public key to authorized_keys
mkdir -p /home/deploy/.ssh
echo "<contents of cryptobot_deploy.pub>" >> /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# Verify access
ssh -i cryptobot_deploy deploy@crypto-bot.example.com "docker ps"
```

### Step 3: Add Secrets to GitHub

Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

Click "New repository secret" for each:

```
Name: VPS_HOST
Value: crypto-bot.example.com

Name: VPS_USER
Value: deploy

Name: VPS_SSH_PRIVATE_KEY
Value: (contents of cryptobot_deploy, including BEGIN/END lines)

Name: POSTGRES_PASSWORD_PROD
Value: (generate: openssl rand -base64 24)

Name: MINIO_ROOT_PASSWORD_PROD
Value: (generate: openssl rand -base64 24)

Name: API_SECRET_KEY_PROD
Value: (generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))")

Name: GF_SECURITY_ADMIN_PASSWORD_PROD
Value: (generate: openssl rand -base64 24)
```

### Step 4: Create .env.production Template

In the CI workflow, create `.env` on VPS using GitHub Secrets:

```yaml
# .github/workflows/deploy-prod.yml
- name: Create production .env on VPS
  env:
    POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD_PROD }}
    MINIO_ROOT_PASSWORD: ${{ secrets.MINIO_ROOT_PASSWORD_PROD }}
    API_SECRET_KEY: ${{ secrets.API_SECRET_KEY_PROD }}
    # ... etc
  run: |
    ssh -i ${{ runner.temp }}/deploy_key deploy@${{ secrets.VPS_HOST }} << 'ENVSCRIPT'
      cat > /opt/cryptobot/.env << 'EOF'
      POSTGRES_PASSWORD=${{ env.POSTGRES_PASSWORD }}
      MINIO_ROOT_PASSWORD=${{ env.MINIO_ROOT_PASSWORD }}
      API_SECRET_KEY=${{ env.API_SECRET_KEY }}
      # ... all other variables
      EOF
      chmod 600 /opt/cryptobot/.env
    ENVSCRIPT
```

---

## GitHub Actions Workflow Example

See `.github/workflows/ci-cd.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:2.14.2-pg16
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -e . && pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=src --cov-fail-under=80
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
      - uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: "cryptobot:latest"

  deploy-prod:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Install SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VPS_SSH_PRIVATE_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts
      
      - name: Deploy to VPS
        run: |
          ssh -i ~/.ssh/deploy_key ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} << 'DEPLOY'
            cd /opt/cryptobot
            git pull origin main
            docker-compose pull
            docker-compose up -d
            sleep 10
            curl -f https://crypto-bot.example.com/health || exit 1
          DEPLOY
      
      - name: Smoke tests
        run: |
          curl -f https://crypto-bot.example.com/api/health
          curl -f https://crypto-bot.example.com/  # frontend
```

---

## Secret Rotation Checklist

### Every 90 Days (Critical)

- [ ] `POSTGRES_PASSWORD_PROD`
- [ ] `MINIO_ROOT_PASSWORD_PROD`
- [ ] `GF_SECURITY_ADMIN_PASSWORD_PROD`

**Procedure**:
1. Generate new secret: `openssl rand -base64 24`
2. Update GitHub Secret
3. SSH to VPS and update `.env` file
4. Restart affected services: `docker-compose restart <service>`
5. Verify health: `curl https://crypto-bot.example.com/health`
6. Document in PRODUCTION_RUNBOOK.md § Secret Rotation Log

### Every 180 Days (High Sensitivity)

- [ ] `API_SECRET_KEY_PROD`

**Procedure**:
1. Generate new key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Update GitHub Secret
3. Update VPS `.env`
4. Restart API: `docker-compose restart api`
5. All existing JWT tokens become invalid (users must re-login)
6. Verify: `curl -H "Authorization: Bearer <old_token>" https://crypto-bot.example.com/api/profile` should return 401

### Every 1 Year (SSH Key)

- [ ] `VPS_SSH_PRIVATE_KEY` (if not using ed25519 with very short expiry)

**Procedure**:
1. Generate new keypair: `ssh-keygen -t ed25519 -f cryptobot_deploy -N ""`
2. Upload public key to VPS: `/home/deploy/.ssh/authorized_keys`
3. Update GitHub Secret with new private key
4. Test access before removing old key
5. Remove old key from authorized_keys

---

## Troubleshooting

### "Permission denied (publickey)" in GitHub Actions

**Cause**: SSH private key not properly formatted or imported.

**Fix**:
```bash
# Verify key format
ssh-keygen -l -f cryptobot_deploy

# Check GitHub Secret value includes BEGIN/END lines:
# -----BEGIN RSA PRIVATE KEY-----
# ... base64 content ...
# -----END RSA PRIVATE KEY-----
```

### Workflow Fails with "Secret not found"

**Cause**: Secret name mismatch between workflow and GitHub settings.

**Fix**:
```bash
# In workflow, reference as:
${{ secrets.VPS_SSH_PRIVATE_KEY }}  # matches "VPS_SSH_PRIVATE_KEY"

# NOT:
${{ secrets.vps_ssh_private_key }}  # wrong case
${{ secrets.SSH_KEY }}              # wrong name
```

### "Timeout waiting for VPS"

**Cause**: SSH key auth failed; VPS is not accessible.

**Fix**:
```bash
# Test locally first
ssh -i cryptobot_deploy deploy@crypto-bot.example.com "hostname"

# If that works, check GitHub Secret is exactly the same
# If it fails, verify:
# 1. Public key is in /home/deploy/.ssh/authorized_keys
# 2. VPS SSH port is 22 (not custom)
# 3. Firewall allows SSH from GitHub Actions (0.0.0.0/0)
```

---

## Best Practices

- [ ] Never log secrets in workflow output
- [ ] Rotate SSH keys yearly
- [ ] Rotate API keys on suspected breach
- [ ] Use separate secrets for staging vs. production
- [ ] Document all secrets in this file (without values)
- [ ] Test secret access in a non-critical deployment first
- [ ] Set up alerts for secret access in GitHub audit logs

---

## Next Steps

1. Generate SSH keypair and deploy credentials
2. Add all secrets to GitHub Settings
3. Test CI/CD pipeline with a test deployment
4. Set up automated secret rotation reminders (calendar, ticket, etc.)
5. Monitor GitHub audit log for secret access

