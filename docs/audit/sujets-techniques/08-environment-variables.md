# Environment Variables & Configuration

**Status**: Phase 3 (Medium priority) documentation  
**Date**: 2026-03-12  
**Category**: C4 — DevOps documentation

---

## Overview

All Crypto Bot services are configured via environment variables defined in a `.env` file. This document categorizes variables, explains their purpose, and provides guidance on setting secure values.

**Golden Rule**: `.env` is the single source of truth for all configuration. It is **NEVER committed to git** and must be kept secure.

---

## Variable Categories

### 1. Required (Blocking) — Must Set Before `docker-compose up`

These variables have no sensible defaults. The application **fails fast** on startup if missing.

| Variable | Purpose | Example | Min Length | Notes |
|----------|---------|---------|----------|-------|
| `POSTGRES_PASSWORD` | TimescaleDB admin password | `MyP@ssw0rd2025!secure` | 16 chars | Mixed case, numbers, symbols |
| `MINIO_ROOT_PASSWORD` | MinIO S3 admin password | `MyP@ssw0rd2025!secure` | 16 chars | Must match AWS_SECRET_ACCESS_KEY |
| `API_SECRET_KEY` | JWT signing key (FastAPI) | `your-random-32-character-secret-key-here!` | 32 chars | Use `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin login password | `MyP@ssw0rd2025!secure` | 16 chars | Access at http://localhost:3000 |

### 2. Optional (Feature Toggles) — Services Gracefully Disabled if Empty

These variables enable optional services. If not provided, the feature is disabled with a warning log.

| Variable | Purpose | Example | Default Behavior |
|----------|---------|---------|------------------|
| `COINGECKO_API_KEY` | CoinGecko API key (faster rate limits) | `xxxxxxxxxxxxxxxx` | Uses free public API (1/sec) |
| `OPENAI_API_KEY` | OpenAI ChatGPT API key (chatbot) | `sk-xxxxxxxx` | Chatbot disabled; returns 501 Not Implemented |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (alternative) | `sk-ant-xxxxxxxx` | Falls back to OpenAI if empty |

### 3. Derived (Automatic) — Computed from Other Variables

These are automatically set by `docker-compose.yml` or `src/shared/config.py`. **DO NOT change manually** unless you modify the service definitions.

| Variable | Computed From | Purpose |
|----------|---------------|---------|
| `DATABASE_URL` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | SQLAlchemy connection string |
| `AWS_ACCESS_KEY_ID` | `MINIO_ROOT_USER` | MinIO/S3 access key (must match) |
| `AWS_SECRET_ACCESS_KEY` | `MINIO_ROOT_PASSWORD` | MinIO/S3 secret key (must match) |

### 4. Service URLs (Network Configuration)

These are set per environment (dev, staging, prod). Change only when modifying Docker Compose or VPS setup.

| Variable | Dev (Compose) | Staging/Prod (VPS) | Purpose |
|----------|---------------|-------------------|---------|
| `API_HOST` | `0.0.0.0` | `127.0.0.1` | FastAPI bind address |
| `API_PORT` | `8000` | `8000` | FastAPI bind port |
| `API_URL` | `http://api:8000` | `https://crypto-bot.example.com/api` | Frontend → Backend URL |
| `MINIO_ENDPOINT` | `http://minio:9000` | `http://minio:9000` | S3 endpoint (internal Docker network) |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | `http://mlflow:5000` | MLflow server URL |

### 5. Feature Flags & Tuning Parameters

These control behavior. Sensible defaults are set in `src/shared/config.py`, but can be overridden via `.env`.

| Variable | Default | Range | Purpose |
|----------|---------|-------|---------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Python logging verbosity |
| `JWT_EXPIRATION_HOURS` | `24` | 1-720 | JWT access token lifetime (hours) |
| `CORS_ORIGINS` | `["http://localhost:8501"]` | JSON list | Allowed frontend origins for CORS |
| `ETL_SCHEDULE_MINUTES` | `15` | 5-1440 | OHLCV collection interval |
| `ML_BACKTEST_LOOKBACK_DAYS` | `365` | 30-3650 | Historical data for training |

---

## Environment-Specific Templates

### Development (Local Docker Compose)

`.env` (created from `.env.example`)

```bash
# Database
POSTGRES_DB=cryptobot
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=dev_password_123456789  # min 16 chars

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123456789  # min 16 chars
MINIO_ENDPOINT=http://minio:9000

# API
API_SECRET_KEY=dev-secret-key-32-chars-or-longer!
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:8501"]
LOG_LEVEL=DEBUG

# Frontend
API_URL=http://api:8000

# Grafana
GF_SECURITY_ADMIN_PASSWORD=admin123456789

# AWS/MLflow (points to MinIO)
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin123456789
MLFLOW_TRACKING_URI=http://mlflow:5000
```

### Staging (VPS with HTTPS)

`.env.staging` (example — symlink or copy to `.env` on VPS)

```bash
# Database
POSTGRES_DB=cryptobot
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=<generate with: openssl rand -base64 24>

# MinIO
MINIO_ROOT_USER=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(16))">
MINIO_ROOT_PASSWORD=<generate with: openssl rand -base64 24>
MINIO_ENDPOINT=http://minio:9000

# API
API_SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=["https://staging.crypto-bot.example.com"]
LOG_LEVEL=INFO

# Frontend
API_URL=https://staging.crypto-bot.example.com/api

# Grafana
GF_SECURITY_ADMIN_PASSWORD=<generate secure password>

# AWS/MLflow
AWS_ACCESS_KEY_ID=<MINIO_ROOT_USER>
AWS_SECRET_ACCESS_KEY=<MINIO_ROOT_PASSWORD>
MLFLOW_TRACKING_URI=http://mlflow:5000

# Optional APIs
COINGECKO_API_KEY=<your demo key if available>
OPENAI_API_KEY=<optional>

# Feature flags
ETL_SCHEDULE_MINUTES=15
ML_BACKTEST_LOOKBACK_DAYS=365
```

### Production (VPS with HTTPS + Monitoring)

`.env.production` (example — **NEVER commit**, use VPS secrets manager)

```bash
# Database (hardened)
POSTGRES_DB=cryptobot_prod
POSTGRES_USER=cryptobot_prod
POSTGRES_PASSWORD=<rotate every 90 days>

# MinIO (access restricted to internal network)
MINIO_ROOT_USER=<rotate every 90 days>
MINIO_ROOT_PASSWORD=<rotate every 90 days>
MINIO_ENDPOINT=http://minio:9000

# API (production hardening)
API_SECRET_KEY=<rotate every 180 days>
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=["https://crypto-bot.example.com"]
LOG_LEVEL=WARNING

# Frontend
API_URL=https://crypto-bot.example.com/api

# Grafana (production dashboard)
GF_SECURITY_ADMIN_PASSWORD=<rotate every 90 days>

# AWS/MLflow (production artifact storage)
AWS_ACCESS_KEY_ID=<MINIO_ROOT_USER>
AWS_SECRET_ACCESS_KEY=<MINIO_ROOT_PASSWORD>
MLFLOW_TRACKING_URI=http://mlflow:5000

# Paid APIs (if budget available)
COINGECKO_API_KEY=<your paid tier key>
OPENAI_API_KEY=<production key>

# Monitoring/Alerting
LOG_LEVEL=WARNING
ETL_SCHEDULE_MINUTES=15
ML_BACKTEST_LOOKBACK_DAYS=730  # 2 years for stability
JWT_EXPIRATION_HOURS=8  # shorter lifetime for prod
```

---

## Secret Generation Best Practices

### Password Generation

```bash
# Option 1: OpenSSL (cryptographically strong)
openssl rand -base64 24

# Option 2: Python secrets module
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 3: /dev/urandom
head -c 32 /dev/urandom | base64
```

### JWT Secret Generation

```bash
# Must be >= 32 characters
python3 << 'PYTHON'
import secrets
key = secrets.token_urlsafe(32)
print(f"API_SECRET_KEY={key}")
PYTHON
```

### Password Requirements Checklist

- [ ] Minimum 16 characters (32 recommended for critical secrets)
- [ ] At least one uppercase letter
- [ ] At least one lowercase letter
- [ ] At least one digit
- [ ] At least one special character (!@#$%^&*)
- [ ] No dictionary words
- [ ] Not reused from other systems

---

## Secret Rotation Policy

**Critical Secrets** (rotate every 90 days):
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_PASSWORD`
- `GF_SECURITY_ADMIN_PASSWORD`

**High-Sensitivity Secrets** (rotate every 180 days):
- `API_SECRET_KEY`
- `AWS_SECRET_ACCESS_KEY`

**External API Keys** (rotate on breach or key exposure):
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `COINGECKO_API_KEY`

### Rotation Procedure (VPS)

1. **Generate new secret**: `openssl rand -base64 24`
2. **Update on VPS** (via SSH or secrets manager):
   ```bash
   # SSH into VPS
   ssh user@vps.example.com
   
   # Edit .env
   nano /opt/cryptobot/.env
   
   # Update the variable
   POSTGRES_PASSWORD=<new_value>
   
   # Restart services
   docker-compose restart timescaledb api frontend
   
   # Verify health
   curl https://crypto-bot.example.com/health
   ```
3. **Document rotation**: Log in rotation log (see PRODUCTION_RUNBOOK.md § Incident Log)
4. **Update secure storage**: If using Vercel Secrets or similar, update there too

---

## Configuration Loading Order

The application loads configuration in this order (last wins):

1. **Defaults** — compiled in `src/shared/config.py`
2. **Environment variables** — from `.env` file
3. **Command-line flags** — (not used in Docker; for local dev)

Example in code:

```python
from src.shared.config import settings

# Loaded from .env or defaults
print(settings.postgres_password)  # from POSTGRES_PASSWORD
print(settings.api_port)           # from API_PORT or default 8000
```

---

## Troubleshooting

### "ValueError: POSTGRES_PASSWORD not set"

**Cause**: `.env` file missing or variable not defined.

**Fix**:
```bash
cp .env.example .env
# Edit .env and fill in all CHANGE_ME values
docker-compose restart
```

### "InvalidCredentials: MinIO authentication failed"

**Cause**: `AWS_SECRET_ACCESS_KEY` doesn't match `MINIO_ROOT_PASSWORD`.

**Fix**:
```bash
# Ensure these match in .env
MINIO_ROOT_PASSWORD=your_password_here
AWS_SECRET_ACCESS_KEY=your_password_here  # MUST BE IDENTICAL

docker-compose restart minio
```

### "OperationalError: could not translate host name"

**Cause**: Service URLs incorrect for VPS (using Docker Compose internal names).

**Fix**: On VPS, update `.env`:
```bash
# Instead of: MINIO_ENDPOINT=http://minio:9000
# Use internal Docker network:
MINIO_ENDPOINT=http://minio:9000  # still works in Docker Compose network
# Or if minio is on different host:
MINIO_ENDPOINT=http://192.168.1.50:9000
```

### "CORS policy: Cross-Origin Request Blocked"

**Cause**: `CORS_ORIGINS` doesn't include frontend URL.

**Fix**:
```bash
# In .env, update:
CORS_ORIGINS=["https://your-domain.com"]  # JSON array as string
```

---

## Security Checklist

- [ ] `.env` is in `.gitignore` (never committed)
- [ ] `.env.example` contains only placeholders (no real secrets)
- [ ] All required variables are set in `.env` before `docker-compose up`
- [ ] Database password is 16+ characters with mixed case, numbers, symbols
- [ ] API_SECRET_KEY is 32+ random characters
- [ ] MinIO and AWS secrets match exactly
- [ ] CORS_ORIGINS restricted to known frontend domains
- [ ] VPS `.env` is secured with 0600 file permissions: `chmod 600 .env`
- [ ] Secrets are backed up in a secure location (password manager, Vault)
- [ ] Never share `.env` file via email, Slack, or GitHub

---

## Next Steps

1. **Local development**: `cp .env.example .env` and fill in values
2. **VPS setup**: Use `.env.production` template; secure with `chmod 600 .env`
3. **CI/CD**: Configure GitHub Secrets (see Appendix § GitHub Secrets)
4. **Monitoring**: Set up secret rotation alerts (see PRODUCTION_RUNBOOK.md § Secret Rotation)

---

## Appendix: GitHub Secrets Configuration

For automated deployments to VPS, configure these as GitHub Secrets:

| Secret Name | Value | Rotation |
|-------------|-------|----------|
| `VPS_HOST` | `crypto-bot.example.com` | Never |
| `VPS_USER` | `deploy` | Never |
| `VPS_SSH_KEY` | SSH private key (4096-bit) | Every 1 year |
| `POSTGRES_PASSWORD_PROD` | Same as `.env.production` | Every 90 days |
| `MINIO_ROOT_PASSWORD_PROD` | Same as `.env.production` | Every 90 days |
| `API_SECRET_KEY_PROD` | Same as `.env.production` | Every 180 days |

Access via: GitHub Repo → Settings → Secrets and variables → Actions

