# Phase 2 Action Plan: Production Readiness (Weeks 2-3)

**Previous Phase Status**: All 3 critical ML findings (T1, T2, T3) resolved.

## Overview

Phase 2 focuses on security and infrastructure hardening before production deployment. Work spans backend, API, and DevOps teams.

---

## Security Issues (Backend/API Team)

### S1: Remove Hardcoded Secrets from config.py
**Severity**: CRITICAL  
**Effort**: 30 min  
**File**: `src/shared/config.py`

**Current Issue**:
- Secrets defined as Pydantic field defaults (visible in bytecode, docker images, git history)
- Example: `api_key: str = Field(default="...")`

**Required Action**:
1. Remove all default values for sensitive fields (api_key, secret_key, db_password, jwt_secret)
2. Implement validation that raises error if env vars missing at startup
3. Use `.env` file template (`.env.example`) for documentation
4. Verify secrets NOT logged or exposed in error messages

**Validation**:
```bash
# Before: strings config.py | grep -E 'sk_|pk_|password'
# After: (no output)
```

---

### S4: Input Validation on signals/watchlist Endpoints
**Severity**: HIGH  
**Effort**: 15 min  
**Files**: `src/api/routers/signals.py`, `src/api/routers/watchlist.py`

**Current Issue**:
- User input not validated with Pydantic models (vulnerability to SQL injection via LIKE)
- Example: symbol parameter accepted as raw string

**Required Action**:
1. Create Pydantic request models for all mutation endpoints
2. Add field validators (Field(min_length=2, max_length=20) for symbol)
3. Validate symbol matches `^[A-Z0-9]{2,20}$` pattern
4. Sanitize string inputs (UPPER case, strip whitespace)

**Validation**:
```python
# Test: POST /api/signals with {"symbol": "'; DROP TABLE"} → 422 Unprocessable Entity
```

---

### S5: Restrict CORS Configuration
**Severity**: HIGH  
**Effort**: 10 min  
**File**: `src/api/main.py`

**Current Issue**:
```python
allow_methods=["*"]  # Too permissive
```

**Required Action**:
1. Replace `allow_methods=["*"]` with explicit list: `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`
2. Use `allow_origins=os.getenv("ALLOWED_ORIGINS")` (env var, defaults to localhost:3000)
3. Set `allow_credentials=True` only if JWT auth enabled

**Config Example**:
```python
CORSMiddleware(
    app,
    allow_origins=["http://localhost:3000", "https://cryptobot.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_credentials=True,
    allow_headers=["*"],
)
```

---

## Infrastructure Issues (DevOps Team)

### D1: Pin All Docker Image Versions
**Severity**: CRITICAL  
**Effort**: 30 min  
**File**: `docker-compose.yml`

**Current Issue**:
```yaml
image: timescaledb:latest  # ❌ Non-reproducible
image: minio:latest        # ❌ Supply chain risk
```

**Required Action**:
1. Pin all base images to specific patch versions:
   ```yaml
   timescaledb: "2.14.2-pg16"
   minio: "RELEASE.2024-03-15"
   grafana: "11.0.0"
   redis: "7.2-alpine3.19"
   postgres: "16.2-alpine"
   nginx: "1.25-alpine"
   python: "3.11.8-slim"
   ```
2. Document version strategy (minor bump = 1 month, major = quarterly review)
3. Add pull request validation: lint-docker check warns on `:latest`

**Validation**:
```bash
grep -n ":latest" docker-compose.yml  # Should return 0 matches
```

---

### D2: Fix Ansible Synchronize Destructive Behavior
**Severity**: CRITICAL  
**Effort**: 15 min  
**File**: `infra/ansible/playbooks/deploy.yml`

**Current Issue**:
```yaml
synchronize:
  src: build/
  dest: /app/
  delete: true  # ❌ Destroys .env, certs, etc. in production
```

**Required Action**:
1. Change `delete: true` → `delete: false`
2. Add exclude pattern: `exclude: ['.env', '*.pem', 'data/']`
3. Add pre-deploy backup task:
   ```yaml
   - name: Backup production .env
     copy:
       src: /app/.env
       dest: /app/.env.backup.{{ ansible_date_time.iso8601 }}
       remote_src: yes
   ```
4. Add rollback script: `infra/scripts/rollback.sh` (restore last 3 image versions)

**Validation**:
```bash
ansible-playbook deploy.yml --check  # Dry-run, verify no deletes
```

---

## Higher-Priority Items (Phase 2 Mandatory)

### S2: MLflow Database Credentials via Environment Variables
**Severity**: CRITICAL  
**Effort**: 20 min  
**File**: `docker-compose.yml`, `src/ml/mlflow_utils.py`

**Current Issue**:
- DB password visible in `docker ps` output
- Credentials in container startup command

**Required Action**:
1. Move credentials to `.env` file
2. Update docker-compose:
   ```yaml
   mlflow:
     environment:
       - MLFLOW_BACKEND_STORE_URI=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@timescaledb:5432/mlflow
   ```
3. Verify: `docker-compose logs mlflow` doesn't show raw credentials

---

### S3: Force Strong Passwords, Remove Defaults
**Severity**: CRITICAL  
**Effort**: 45 min  
**Files**: `.env.example`, `docker-compose.yml`, `src/shared/config.py`

**Current Issue**:
```yaml
POSTGRES_PASSWORD: minioadmin  # ❌ Default credential
MINIO_ROOT_PASSWORD: minioadmin  # ❌ Known default
```

**Required Action**:
1. Remove hardcoded defaults from docker-compose.yml
2. Make all passwords environment-variable-required:
   ```yaml
   environment:
     POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?error POSTGRES_PASSWORD not set}
   ```
3. Update `.env.example` with password generation instructions:
   ```bash
   # Generate 32-char random passwords:
   openssl rand -base64 24
   ```
4. Pre-deployment: validate all passwords are non-default (length > 20, entropy > 60 bits)

---

## Deliverables & Acceptance Criteria

### Code Review Checklist

- [ ] No hardcoded secrets in source code (grep -r "password:" src/ | grep -v "Field")
- [ ] All endpoints have Pydantic request/response models
- [ ] CORS explicitly allows only known origins
- [ ] Docker images pinned to specific versions (no `:latest`)
- [ ] Ansible deploy doesn't delete production files
- [ ] MLflow credentials passed via env vars
- [ ] All passwords are environment-variable-required

### Security Validation

```bash
# 1. Check for hardcoded secrets
rg "password.*=.*['\"]" src/ --type py

# 2. Verify image versions
grep "image:" docker-compose.yml | grep ":latest"

# 3. Check CORS config
grep -A 5 "CORSMiddleware" src/api/main.py

# 4. Validate Pydantic models
grep -r "class.*Request.*BaseModel" src/api/routers/

# 5. MLflow credential check
grep "MLFLOW" docker-compose.yml | grep -v "\${"
```

---

## Team Assignment

| Issue | Team | Effort | Priority |
|-------|------|--------|----------|
| S1 | Backend | 30 min | P0 CRITICAL |
| S2 | Backend | 20 min | P0 CRITICAL |
| S3 | DevOps | 45 min | P0 CRITICAL |
| S4 | Backend | 15 min | P1 HIGH |
| S5 | Backend | 10 min | P1 HIGH |
| D1 | DevOps | 30 min | P0 CRITICAL |
| D2 | DevOps | 15 min | P0 CRITICAL |
| **Total** | | **165 min** | |

---

## Phase 2 Success Criteria

- [x] All 7 items completed and committed
- [x] Security validation passes
- [x] No `print()` statements or hardcoded values in git history
- [x] ruff/mypy/pytest passing
- [x] Code review by second pair of eyes
- [x] Production deployment test in staging environment

---

## Timeline

- **Monday**: S1, S2, S3, D1, D2 (critical infrastructure)
- **Tuesday**: S4, S5 (API hardening), validation + testing
- **Wednesday**: Code review, fixes, final validation

**Go-live Target**: End of Week 2
