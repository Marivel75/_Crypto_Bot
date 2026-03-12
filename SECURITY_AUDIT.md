# Security Audit Report: Crypto Bot

**Date:** 2026-03-12
**Scope:** Full codebase security assessment
**Status:** CRITICAL issues identified — do NOT deploy to production until resolved

---

## Executive Summary

The crypto-bot project implements strong security practices in most areas but has **3 CRITICAL vulnerabilities** that must be addressed before production deployment. Key findings:

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 3 | Must fix immediately |
| HIGH | 5 | Should fix before production |
| MEDIUM | 3 | Address soon |
| LOW | 1 | Fix when convenient |

**Risk Assessment:** Current state is suitable for **development only**. The CRITICAL issues expose database credentials, API secrets, and default credentials in production containers.

---

## CRITICAL VULNERABILITIES

### 1. Hardcoded Development Secrets in `src/shared/config.py` (S105, S104)

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/shared/config.py` (lines 18, 21, 28, 33)

**Issue:** Default Pydantic settings contain plaintext secrets that become embedded in Python bytecode and Docker images:

```python
database_url: str = "postgresql://cryptobot:password@timescaledb:5432/cryptobot"
postgres_password: str = "password"  # noqa: S105
minio_root_password: str = "minioadmin"  # noqa: S105
api_secret_key: str = "dev-secret-key"  # noqa: S105
```

**Risk:**
- Secrets visible in `.pyc` compiled bytecode
- Embedded in Docker image layers (visible via `docker history`)
- Accessible via decompilers or image inspection
- No way to use different secrets in production without modifying code

**Remediation:**

```python
from pydantic import Field

class Settings(BaseSettings):
    # Remove all default values. Make secrets REQUIRED.
    database_url: str = Field(..., description="PostgreSQL connection string")
    postgres_password: str = Field(..., description="PostgreSQL password")
    minio_root_password: str = Field(..., description="MinIO root password")
    api_secret_key: str = Field(..., min_length=32, description="JWT secret key (≥32 chars)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
```

**Verification:** When running, if `.env` is missing required variables, the app will fail fast at startup with a clear error message.

---

### 2. Database Password Exposed in MLflow Command String

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/docker-compose.yml` (lines 67-72)

**Issue:** PostgreSQL password is interpolated directly into the MLflow command-line arguments, visible via `docker ps`:

```yaml
command: >
  mlflow server
  --host 0.0.0.0
  --port 5000
  --backend-store-uri postgresql://${POSTGRES_USER:-cryptobot}:${POSTGRES_PASSWORD}@timescaledb:5432/${POSTGRES_DB:-cryptobot}
```

**Risk:**
- Anyone with `docker ps` access can read the password
- Process argument lists are world-readable in `/proc/[pid]/cmdline`
- Credentials appear in container logs and monitoring tools
- Violates principle of least privilege

**Remediation:** Use environment variables instead of command arguments:

```yaml
mlflow:
  build:
    context: ./src/ml
    dockerfile: Dockerfile.mlflow
  restart: unless-stopped
  environment:
    MLFLOW_TRACKING_URI: http://localhost:5000
    MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://mlflow-artifacts/
    AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
    AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
    MLFLOW_S3_ENDPOINT_URL: http://minio:9000
    # NEW: Pass DB credentials via env instead of CLI args
    MLFLOW_BACKEND_STORE_USER: ${POSTGRES_USER:-cryptobot}
    MLFLOW_BACKEND_STORE_PASSWORD: ${POSTGRES_PASSWORD}
    MLFLOW_BACKEND_STORE_HOST: timescaledb
    MLFLOW_BACKEND_STORE_PORT: 5432
    MLFLOW_BACKEND_STORE_DB: ${POSTGRES_DB:-cryptobot}
  command: >
    mlflow server
    --host 0.0.0.0
    --port 5000
    --backend-store-uri postgresql://$MLFLOW_BACKEND_STORE_USER:$MLFLOW_BACKEND_STORE_PASSWORD@$MLFLOW_BACKEND_STORE_HOST:$MLFLOW_BACKEND_STORE_PORT/$MLFLOW_BACKEND_STORE_DB
```

Similarly for postgres-exporter (line 305) — move `DATA_SOURCE_NAME` to environment variables if possible.

---

### 3. Default Credentials in `docker-compose.yml` Services

**Location:** Multiple services in `/home/jules/Documents/3-git/DTSC/amau/cryptobot/docker-compose.yml`

**Issue:** Default credentials are used across services with no production override:

- **Grafana** (lines 262-263): `admin:admin` hardcoded
- **MinIO** (lines 33-34): `minioadmin:minioadmin` hardcoded
- **PostgreSQL** (lines 7-8): `cryptobot:password` with `CHANGE_ME` placeholder in `.env.example`

**Risk:**
- Default credentials persist in production unless explicitly changed
- Attackers target well-known defaults (Shodan searches for `minioadmin`)
- Compliance failure (CIS benchmarks, OWASP)

**Remediation:**

1. **Enforce non-empty validation in config:**

```python
from pydantic import field_validator

class Settings(BaseSettings):
    grafana_admin_password: str = Field(
        ...,
        min_length=12,
        description="Grafana admin password (≥12 chars, no 'admin' default)"
    )

    @field_validator("grafana_admin_password")
    @classmethod
    def not_default(cls, v: str) -> str:
        if v in ("admin", "password", "minioadmin", "CHANGE_ME"):
            raise ValueError("Cannot use default or weak password")
        return v
```

2. **Remove defaults from compose:**

```yaml
grafana:
  environment:
    GF_SECURITY_ADMIN_USER: ${GF_SECURITY_ADMIN_USER}  # No default
    GF_SECURITY_ADMIN_PASSWORD: ${GF_SECURITY_ADMIN_PASSWORD}  # No default
```

3. **Update `.env.example`:**

```bash
# Database
POSTGRES_PASSWORD=<generate strong 16+ char password>
MINIO_ROOT_PASSWORD=<generate strong 16+ char password>
GF_SECURITY_ADMIN_PASSWORD=<generate strong 16+ char password>
```

---

## HIGH SEVERITY ISSUES

### 4. Missing Input Validation on Multiple Endpoints

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/api/routers/signals.py` (line 56) and `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/api/routers/watchlist.py` (line 47)

**Issue:** Path parameters lack validation patterns, allowing injection of special characters:

**signals.py** — `get_by_symbol` endpoint (line 56):
```python
async def get_by_symbol(
    symbol: str,  # NO VALIDATION
    timeframe: str | None = Query(None),  # NO VALIDATION
    ...
):
    signals, total = await signal_service.get_by_symbol(db, symbol, timeframe, limit, page)
```

**watchlist.py** — `remove_symbol` endpoint (line 47):
```python
async def remove_symbol(
    symbol: str,  # NO VALIDATION
    db: AsyncSession = Depends(get_db),
    ...
):
    await user_data_service.remove_watchlist_symbol(db, str(current_user.id), symbol)
```

**Risk:**
- Attackers can inject symbols with SQL-like characters: `"; DROP --`, `%` wildcards
- Although SQLAlchemy ORM provides parameterization, unvalidated input violates defense-in-depth
- Could cause LIKE queries to match unintended records

**Remediation:**

```python
from fastapi import Path, Query

@router.get("/{symbol}")
async def get_by_symbol(
    symbol: str = Path(..., pattern=r"^[A-Z0-9]+$", max_length=20),
    timeframe: str | None = Query(None, pattern=r"^\d+[mhDWM]$"),
    ...
):
    ...

@router.delete("/{symbol}")
async def remove_symbol(
    symbol: str = Path(..., pattern=r"^[A-Z0-9]+$", max_length=20),
    ...
):
    ...
```

Follow the pattern already used in `/crypto.py` (lines 43-44, 64-65).

---

### 5. CORS Misconfiguration (Over-Permissive Methods and Headers)

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/api/main.py` (lines 62-63)

**Issue:** CORS middleware allows all HTTP methods and headers:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # PROBLEM: allows DELETE, PATCH, HEAD, etc.
    allow_headers=["*"],  # PROBLEM: allows any header including X-Custom-Admin
)
```

**Risk:**
- Allows attackers to make CROSS-ORIGIN DELETE requests (if frontend is compromised)
- Accepts any custom headers (could bypass validation if app relies on headers for auth)
- Violates least-privilege principle

**Remediation:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit list
    allow_headers=[
        "content-type",
        "authorization",
        "accept",
        "origin",
    ],  # Explicit list
    max_age=3600,
)
```

---

### 6. Nginx HTTPS Redirect Commented Out

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/infra/nginx/nginx.conf` (lines 19-20)

**Issue:** HTTPS redirect is disabled by default:

```nginx
# Redirect to HTTPS (uncomment when SSL is configured)
# return 301 https://$host$request_uri;
```

**Risk:**
- API credentials (JWT tokens) transmitted in cleartext over HTTP
- Man-in-the-middle attacks can intercept authentication
- Privacy violations for user data
- Fails PCI-DSS, HIPAA, and modern compliance standards

**Remediation:** Enable immediately before production:

```nginx
server {
    listen 80;
    server_name _;
    # Enforce HTTPS for all requests
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name YOUR_DOMAIN;

    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of config ...
}
```

Use certbot with Let's Encrypt for automated certificate management.

---

### 7. Nginx Missing Security Headers on Frontend

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/infra/nginx/nginx.conf` (lines 47-59)

**Issue:** Frontend location block (Streamlit) lacks security headers that API has:

```nginx
location / {
    proxy_pass http://frontend;
    # Missing security headers (present in API block at lines 68-71)
}
```

The API block correctly sets:
- `X-Frame-Options`
- `X-Content-Type-Options`
- `X-XSS-Protection`
- `Referrer-Policy`

**Risk:**
- Frontend vulnerable to clickjacking attacks
- MIME type sniffing could execute scripts
- XSS protection disabled

**Remediation:** Move security headers to a shared block:

```nginx
# Shared security headers for all responses
map $sent_http_content_type $csp_header {
    default "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;";
}

server {
    listen 80;

    # Apply security headers to all locations
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy $csp_header always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    server_tokens off;

    location /api/ { ... }
    location / { ... }
}
```

---

### 8. Base Image Versions Not Pinned (Supply Chain Risk)

**Location:** All Dockerfiles:
- `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/api/Dockerfile` (line 2, 11)
- `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/etl/Dockerfile` (line 2, 11)
- `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/frontend/Dockerfile` (line 2, 11)

**Issue:** Using floating tags (`python:3.11-slim`):

```dockerfile
FROM python:3.11-slim AS builder
```

**Risk:**
- Image contents can change without code changes
- Security patches may introduce breaking changes
- Builds are non-deterministic
- Attackers can inject backdoors via base image updates

**Remediation:** Pin to specific patch version:

```dockerfile
# Pinned to a specific patch version (check latest at hub.docker.com)
FROM python:3.11.9-slim AS builder
```

To find the latest secure version:
```bash
curl -s https://hub.docker.com/v2/repositories/library/python/tags \
  | jq '.results[] | select(.name | contains("3.11")) | .name' \
  | head -20
```

---

## MEDIUM SEVERITY ISSUES

### 9. Brittle LIKE Escape Logic in News Service

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/api/services/news_service.py` (lines 39-40)

**Issue:** Manual LIKE escaping using string replacement, then f-string interpolation:

```python
escaped = keyword.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
conditions.append(NewsArticleOrm.title.ilike(f"%{escaped}%"))
```

**Risk:**
- String replacement order matters; current order is correct but fragile
- f-string with escaped string is error-prone
- Better alternatives exist in SQLAlchemy

**Remediation:** Use SQLAlchemy's native `escape` parameter (PEP 249):

```python
from sqlalchemy import func, literal_column

# Option 1: Use SQLAlchemy's concat with escape
if keyword is not None:
    # SQLAlchemy handles escaping internally
    conditions.append(NewsArticleOrm.title.ilike(f"%{func.lower(keyword)}%", escape="\\"))

# Option 2: Whitelist validation (preferred for security)
if keyword is not None:
    # Only allow alphanumeric, spaces, hyphens
    if not re.match(r"^[a-zA-Z0-9\s\-]+$", keyword):
        raise ValidationError("Invalid keyword: only alphanumeric characters allowed")
    conditions.append(NewsArticleOrm.title.ilike(f"%{keyword}%"))
```

---

### 10. Optional `username` Field in JWT Token (Low Security Value)

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/api/services/auth_service.py` (lines 116-118)

**Issue:** JWT payload includes an optional `username` field with no security purpose:

```python
payload: dict = {"sub": user_id, "exp": expire}
if username:
    payload["username"] = username
```

**Risk:**
- Increases token size without security benefit
- Could leak information (usernames are often enumerable)
- Adds complexity to token validation

**Remediation:** Remove the optional username field. Use `sub` (user_id) alone:

```python
payload: dict = {"sub": user_id, "exp": expire}
return jwt.encode(payload, settings.api_secret_key, algorithm=ALGORITHM)
```

If you need username in the response, fetch it from the database after token validation (already done in `get_current_user`).

---

### 11. ETL Healthcheck References Non-Existent Endpoint

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/etl/Dockerfile` (line 29)

**Issue:** Healthcheck tries to call an HTTP endpoint that doesn't exist:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
```

The ETL worker (line 33) runs `python -m src.etl.main`, which is a background job scheduler, not an HTTP server. Port 8080 doesn't exist.

**Risk:**
- Healthcheck always fails
- Docker marks container as unhealthy even when working correctly
- Orchestration systems may kill the container unnecessarily

**Remediation:** Use a Python-based health check:

```dockerfile
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import src.etl; print('OK')" || exit 1
```

Or simply verify Python can import the module (better than network calls for background workers).

---

## LOW SEVERITY ISSUES

### 12. Frontend Configuration Missing API URL Validation

**Location:** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/src/frontend/config.py`

**Issue:** Frontend API URL is read from environment without validation.

**Risk:** If `API_URL` env var is malicious (e.g., `http://attacker.com`), frontend will make requests to attacker server, leaking JWT tokens and user data.

**Remediation:**

```python
from pydantic import HttpUrl

class FrontendSettings(BaseSettings):
    api_url: HttpUrl = Field(
        ...,
        description="Backend API base URL (must be HTTPS in production)"
    )

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: HttpUrl) -> HttpUrl:
        # Ensure HTTPS in production
        if os.getenv("ENVIRONMENT") == "production" and v.scheme != "https":
            raise ValueError("API_URL must use HTTPS in production")
        return v
```

---

## POSITIVE SECURITY FINDINGS

The following areas are correctly implemented:

✅ **Password Hashing:** bcrypt with default 12 rounds (lines 24-31 of auth_service.py)
✅ **JWT Implementation:** HS256 with proper secret key, expiration, validation
✅ **SQL Injection Prevention:** All queries use SQLAlchemy ORM with parameterized queries
✅ **Authentication:** OAuth2PasswordBearer with proper token validation
✅ **Error Handling:** Generic error messages to clients, full logging server-side
✅ **Database Access Control:** Proper ownership verification on user data (user_data_service.py)
✅ **File Operations:** Safe use of `pathlib.Path` with no traversal risks (rules/engine.py)
✅ **No Debug Statements:** No `print()` statements in production code
✅ **Code Quality:** Strong linting with ruff (S flag for security), mypy strict mode
✅ **Docker Security:** Multi-stage builds, non-root user (UID 1001), no privileged mode
✅ **Rate Limiting:** Implemented in Nginx with stricter limits on auth endpoints
✅ **Health Checks:** Configured on all containers with proper conditions
✅ **Dependency Pinning:** Version constraints on all requirements (no floating versions)
✅ **Secret Management:** `.env` properly gitignored, `.env.example` has placeholders
✅ **Input Validation:** Strong Pydantic validators on most endpoints, email validation
✅ **Data Encryption:** Passwords hashed, secrets in env vars, no plaintext in logs

---

## COMPLIANCE MAPPING

| Standard | Finding | Status |
|----------|---------|--------|
| OWASP Top 10 #1 (Injection) | All parameterized queries | ✅ PASS |
| OWASP Top 10 #2 (Auth) | bcrypt + JWT with expiration | ✅ PASS |
| OWASP Top 10 #3 (Sensitive Data) | HTTPS commented out; secrets in defaults | ❌ FAIL (issues #6, #1-3) |
| OWASP Top 10 #5 (Access Control) | Ownership checks on user data | ✅ PASS |
| OWASP Top 10 #7 (XSS) | Framework auto-escaping, CSP needed | ⚠️ PARTIAL (issue #7) |
| CIS Docker Benchmark | Non-root user, health checks, no privileged | ✅ PASS |
| NIST Cryptography | bcrypt, HMAC-SHA256 for JWT | ✅ PASS |
| PCI-DSS 3.2.1 | HTTPS required, not implemented | ❌ FAIL (issue #6) |

---

## REMEDIATION PRIORITY

### Phase 1: CRITICAL (Do First)

1. **Remove hardcoded secrets from `src/shared/config.py`** (Issue #1)
   - Effort: 30 min
   - Risk: Database credentials exposed in bytecode

2. **Move MLflow DB password to environment variables** (Issue #2)
   - Effort: 20 min
   - Risk: Credentials visible in process list

3. **Enforce strong, non-default passwords** (Issue #3)
   - Effort: 45 min
   - Risk: Default credentials exploitable

### Phase 2: HIGH (Before Production)

4. **Add input validation to signals and watchlist endpoints** (Issue #4)
   - Effort: 15 min
   - Risk: Defense-in-depth bypass

5. **Fix CORS configuration** (Issue #5)
   - Effort: 10 min
   - Risk: Cross-origin attacks

6. **Enable HTTPS** (Issue #6)
   - Effort: 1 hour (with Let's Encrypt)
   - Risk: Credentials transmitted in cleartext

7. **Add security headers to frontend** (Issue #7)
   - Effort: 10 min
   - Risk: Clickjacking, MIME-sniffing attacks

### Phase 3: Before First Release

8. **Pin Docker base image versions** (Issue #8)
   - Effort: 10 min
   - Risk: Supply chain attacks

9. **Simplify LIKE escaping** (Issue #9)
   - Effort: 20 min
   - Risk: Future maintainability

10. **Remove username from JWT** (Issue #10)
    - Effort: 5 min
    - Risk: Information leakage

11. **Fix ETL healthcheck** (Issue #11)
    - Effort: 5 min
    - Risk: Container killed by orchestration

12. **Validate frontend API URL** (Issue #12)
    - Effort: 15 min
    - Risk: Token leakage to wrong server

---

## TESTING RECOMMENDATIONS

### Security Test Cases to Add

```python
# Test unauthorized access returns 401, not 500
def test_missing_auth_returns_401(client):
    response = client.get("/api/v1/portfolio")
    assert response.status_code == 401

# Test invalid JWT returns 401, not 500
def test_invalid_jwt_returns_401(client):
    response = client.get(
        "/api/v1/portfolio",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401

# Test symbol injection is rejected
def test_symbol_injection_rejected(client, auth_token):
    response = client.get(
        "/api/v1/signals/BTCUSDT'; DROP TABLE signals; --",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422  # Validation error

# Test CORS restrictions
def test_cors_rejects_unauthorized_origin(client):
    response = client.get(
        "/api/v1/crypto/list",
        headers={"Origin": "https://evil.com"}
    )
    assert "Access-Control-Allow-Origin" not in response.headers

# Test rate limiting
def test_auth_rate_limiting(client):
    for i in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"}
        )
    # After 5 requests/min limit, should return 429
    assert response.status_code == 429
```

---

## DEPLOYMENT CHECKLIST

Before deploying to production:

- [ ] All hardcoded secrets removed from `src/shared/config.py`
- [ ] Environment variables validate against weak/default values
- [ ] MLflow uses environment variables for database credentials
- [ ] Input validation patterns added to signals and watchlist endpoints
- [ ] CORS allows only necessary methods and headers
- [ ] HTTPS redirect enabled and SSL certificates configured
- [ ] Security headers present on all responses (including frontend)
- [ ] Docker base images pinned to specific patch versions
- [ ] ETL healthcheck corrected
- [ ] Frontend API URL validated against malicious values
- [ ] `.env` file created with strong, random passwords
- [ ] All CHANGE_ME placeholders in `.env.example` replaced
- [ ] Security tests passing (authentication, authorization, rate limiting)
- [ ] Dependency audit clean (`pip-audit` or `safety check`)
- [ ] Nginx configuration reviewed and SSL enabled
- [ ] Database backups tested and recovery procedure verified
- [ ] Monitoring and logging configured for security events
- [ ] Incident response plan documented

---

## REFERENCES

- **OWASP Top 10 2021:** https://owasp.org/Top10/
- **CIS Docker Benchmark:** https://www.cisecurity.org/cis-benchmarks/
- **NIST Crypto Guidelines:** https://csrc.nist.gov/publications/detail/sp/800-175b/final
- **PCI-DSS 3.2.1:** https://www.pcisecuritystandards.org/
- **Pydantic Field Validation:** https://docs.pydantic.dev/latest/concepts/validators/
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **SQLAlchemy Security:** https://docs.sqlalchemy.org/en/20/faq/security.html

---

## NEXT STEPS

1. **Week 1:** Address CRITICAL issues (#1, #2, #3)
2. **Week 2:** Address HIGH issues (#4–7)
3. **Before Release:** Address remaining issues (#8–12)
4. **Production:** Run full security test suite and dependency audit

For questions or clarifications, refer to the code sections cited in each finding.

---

**Report Status:** Complete
**Last Updated:** 2026-03-12
**Next Audit:** After security patches applied (2+ weeks)
