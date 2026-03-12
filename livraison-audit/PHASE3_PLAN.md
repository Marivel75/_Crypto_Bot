# Phase 3 — Medium/Low Priority Improvements

**Date**: 2026-03-12  
**Status**: Planning  
**Effort Estimate**: ~13h total  
**Target Completion**: By end of week

---

## Overview

Phase 3 addresses code quality, testing, and DevOps medium-priority issues identified in the audit. Focus areas:

1. **Architecture (A1-A5)** — 4h: Type safety, ORM clarity, API responses
2. **ML Testing (T4-T7)** — 3h: Rule engine unification, data leakage, E2E tests
3. **DevOps (D6-D10)** — 3h: Monitoring, logging, CI caching, Docker Compose
4. **Documentation (C3-C5)** — 2h: Migrations, env vars, rate limiting
5. **Security (S9-S12)** — 1h: Medium/low issues

---

## Task Breakdown

### Architecture (A1-A5) — 4 hours

#### A1: Eliminate `type: ignore[no-any-return]` in api_client.py (1.5h)

**Problem**: 23 `# type: ignore` suppressions masking real type safety issues  
**Root Cause**: `response.json()` returns `Any`, `.get()` on `Any` returns `Any`

**Solution**:
1. Define response wrapper types: `ApiResponse[T]` with deserialization logic
2. Create type stubs for each endpoint (LoginResponse, OHLCVList, etc.)
3. Use Pydantic `model_validate_json()` instead of raw `.json()`
4. Implement `_decode_response()` helper with type narrowing

**Files**:
- `src/frontend/api_client.py` — Rewrite with proper typing

**Test**:
```bash
mypy src/frontend/ --strict  # 0 errors expected
```

---

#### A2: Unify ORM Model Naming (0.5h)

**Problem**: Confusion between `src/shared/orm.py` and `src/shared/db_models.py`  
**Root Cause**: Unclear naming convention; both sound like ORM models

**Solution**:
1. Rename `orm.py` → `db_models.py` (consolidate)
2. Update all imports across codebase
3. Document: ORM models in `src/shared/db_models.py`, Pydantic in `src/shared/models/`

**Files**:
- Rename: `src/shared/orm.py` → `src/shared/db_models.py`
- Update imports in `src/api/`, `src/etl/`, `src/ml/`

**Test**:
```bash
ruff check src/  # no import errors
```

---

#### A3: Add Explicit `response_model` on All API Endpoints (1.5h)

**Problem**: Some endpoints lack `response_model=`, losing type guarantees  
**Root Cause**: Oversight in endpoint definitions

**Solution**:
1. Audit all `@router.get/post/put/delete` decorators
2. Add `response_model=ApiResponse[ResponseType]` on every endpoint
3. Ensure all response types derive from Pydantic BaseModel

**Files**:
- `src/api/routers/*.py` — Add response_model to all endpoints

**Coverage**: auth, crypto, signals, news, portfolio, watchlist, chat, system

**Test**:
```bash
# OpenAPI schema validation
curl http://localhost:8000/api/docs | grep -c '"responses"'  # Should have entries for all endpoints
```

---

#### A4: Config Management — Pass Constants via DependencyInjection (1h)

**Problem**: ML services import `config/indicators.yaml` constants directly  
**Root Cause**: Tight coupling; hard to test with alternate configs

**Solution**:
1. Create `IndicatorConfig` Pydantic model
2. Load once in `src/shared/config.py`
3. Pass via FastAPI `Depends(get_config)`
4. Inject into ML services

**Files**:
- `src/shared/config.py` — Add IndicatorConfig
- `src/ml/rule_engine.py` — Accept config via init

**Test**:
```bash
pytest tests/unit/test_rule_engine.py -v  # Should accept mock config
```

---

#### A5: Extract ETL Job Scheduling from Business Logic (1h)

**Problem**: `src/etl/main.py` mixes APScheduler jobs with data collection logic  
**Root Cause**: Violates Single Responsibility Principle

**Solution**:
1. Create `src/etl/scheduler.py` with job definitions
2. Move pure logic to `src/etl/jobs.py` (already exists; enhance)
3. Keep `main.py` minimal: just app setup + scheduler start

**Files**:
- `src/etl/scheduler.py` (new)
- `src/etl/main.py` (refactor)
- `src/etl/jobs.py` (consolidate logic)

**Test**:
```bash
pytest tests/unit/test_etl_jobs.py -v  # Jobs testable in isolation
```

---

### ML Testing (T4-T7) — 3 hours

#### T4: Unify Rule Engine API (1h)

**Problem**: Rule engine has dual methods: `evaluate()` and `generate_signals()`  
**Root Cause**: Unclear abstraction; confuses users

**Solution**:
1. Consolidate to single `evaluate()` method returning `SignalDecision`
2. Deprecate `generate_signals()`
3. Update all call sites

**Files**:
- `src/ml/rule_engine.py` — Unify API

**Test**:
```bash
pytest tests/unit/test_rule_engine_api.py -v  # Single interface verified
```

---

#### T5: Fix Data Leakage in Backtester (0.5h)

**Problem**: Indicators computed before temporal train/test split  
**Root Cause**: Feature engineering runs on full dataset

**Solution**:
1. Move indicator calculation inside `generate_features()`
2. Ensure it runs AFTER train/test split
3. Add temporal embargo window validation

**Files**:
- `src/ml/backtesting/walk_forward.py` — Reorder operations

**Test**:
```bash
pytest tests/unit/test_walk_forward_backtest.py::test_no_data_leakage -v
```

---

#### T6 & T7: E2E and Regression Tests (1.5h)

**Problem**: No end-to-end signal generation tests; no regression detection  
**Root Cause**: Limited test coverage for ML pipeline

**Solution**:
1. Create `tests/e2e/test_signal_generation_pipeline.py`
   - Load fixture OHLCV data
   - Run full pipeline: ETL → ML → Signal generation
   - Assert signals are generated and conform to schema

2. Create `tests/ml/test_regression_detection.py`
   - Track baseline signal metrics (count, avg confidence)
   - Alert if metrics regress >5% on code changes

**Files**:
- `tests/e2e/test_signal_generation_pipeline.py` (new)
- `tests/ml/test_regression_detection.py` (new)

**Test**:
```bash
pytest tests/e2e/test_signal_generation_pipeline.py -v
```

---

### DevOps (D6-D10) — 3 hours

#### D6: Implement Grafana Alerting Rules (1h)

**Problem**: Grafana installed but no alert rules configured  
**Root Cause**: Setup incomplete

**Solution**:
1. Create `infra/grafana/provisioning/alerts.yml`
2. Define rules for: API latency, error rate, DB connections, disk space, memory
3. Add notification channels (email/webhook)
4. Document alert thresholds in runbook (already done in Phase 2)

**Files**:
- `infra/grafana/provisioning/alerts.yml` (new)
- Update `docker-compose.yml` to mount alerts config

**Thresholds** (from PRODUCTION_RUNBOOK.md):
- API p95 latency > 2s
- Error rate > 0.1%
- DB connections >= 90% of max
- Disk < 10% free
- Memory > 80% of container limit

**Test**:
```bash
curl -s http://localhost:3000/api/alerts | jq '.[]' | wc -l  # Should have >=5 rules
```

---

#### D7: GitHub Actions Secrets Configuration (0.5h)

**Problem**: CI references secrets not configured in GitHub  
**Root Cause**: Setup incomplete

**Solution**:
1. Document required secrets in `PRODUCTION_RUNBOOK.md` (done)
2. List in GitHub repo settings UI (manual)
3. Add comment to `.github/workflows/*.yml` with setup instructions

**Secrets to configure**:
- `DOCKER_REGISTRY_USERNAME`
- `DOCKER_REGISTRY_PASSWORD`
- `VPS_SSH_KEY`
- `VPS_HOST`
- `SLACK_WEBHOOK_URL` (optional)

**Files**:
- `.github/workflows/deploy.yml` — Add comments with setup steps

---

#### D8: Update Docker Compose Version (0.5h)

**Problem**: `docker-compose.yml` declares obsolete `version: "3.8"`  
**Root Cause**: Version ignored since Compose V2; cleanliness issue

**Solution**:
1. Remove `version:` line (Compose V2+ doesn't use it)
2. Update comment to reference modern Compose features

**Files**:
- `docker-compose.yml` — Remove version line

**Test**:
```bash
docker-compose config  # Should validate without warnings
```

---

#### D9: Nginx Log Persistence (0.5h)

**Problem**: Nginx logs lost on container restart  
**Root Cause**: No volume mount for `/var/log/nginx`

**Solution**:
1. Add named volume: `nginx-logs-data`
2. Mount in `docker-compose.yml`: `/var/log/nginx`
3. Add log rotation via logrotate in nginx container

**Files**:
- `docker-compose.yml` — Add nginx logs volume
- `infra/nginx/Dockerfile` — Add logrotate config

**Test**:
```bash
docker-compose exec nginx tail -f /var/log/nginx/access.log  # Should persist
```

---

#### D10: Create `docker-compose.override.yml` Template (0.5h)

**Problem**: Development configuration mixed with production config  
**Root Cause**: Single compose file for all environments

**Solution**:
1. Keep `docker-compose.yml` for production
2. Create `docker-compose.override.yml` (git-ignored) with dev defaults:
   - Lower resource limits
   - Faster timeouts
   - Volume mounts for source code hot reload
   - Disabled HTTPS, enabled debug logging

**Files**:
- `docker-compose.override.yml.example` (template)
- `.gitignore` — Add `docker-compose.override.yml`

**Usage**:
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
docker-compose up  # Automatically merges both files
```

---

### Documentation (C3-C5) — 2 hours

#### C3: Create Alembic Migration Guide (0.5h)

**Problem**: Alembic migrations stagnant; developers unsure how to create new ones  
**Root Cause**: No documentation or workflow

**Solution**:
1. Create `docs/07-database-migrations.md`
2. Steps: `alembic revision --autogenerate`, review, test, commit
3. Examples: add column, rename table, create hypertable
4. Troubleshooting: revision conflicts, rollback procedure

**Files**:
- `docs/07-database-migrations.md` (new)

---

#### C4: Environment Variables Security Guide (0.5h)

**Problem**: Developers unsure which env vars are secrets  
**Root Cause**: No clear documentation

**Solution**:
1. Create `docs/08-environment-variables.md`
2. Categorize: required, optional, secrets, feature flags
3. Rotation policy for secrets
4. Examples of `.env` for different environments

**Files**:
- `docs/08-environment-variables.md` (new)

---

#### C5: API Rate Limiting Documentation (0.5h)

**Problem**: Rate limiting configured in nginx but undocumented  
**Root Cause**: No user-facing documentation

**Solution**:
1. Create `docs/09-rate-limiting.md`
2. Document limits: general (30 req/s), auth (5 req/min)
3. Handling 429 responses
4. Whitelist procedures for trusted clients

**Files**:
- `docs/09-rate-limiting.md` (new)

---

### Security (S9-S12) — 1 hour

#### S9-S12: Medium/Low Security Issues (1h)

**Problem**: Several low-priority security improvements  
**Scope** (from audit):
- S9: Add `X-Content-Type-Options: nosniff` (already done in Phase 2)
- S10: Add `X-Frame-Options: SAMEORIGIN` (already done in Phase 2)
- S11: API versioning consistency (enforce `/api/v1/`)
- S12: Rate limiting headers in responses

**Solution**:
1. Verify S9/S10 in nginx.conf (done)
2. Add custom middleware for rate limit response headers:
   - `X-RateLimit-Limit`
   - `X-RateLimit-Remaining`
   - `X-RateLimit-Reset`
3. Add CI check: all endpoints must have `/api/v1/` prefix

**Files**:
- `src/api/middleware.py` — Add rate limit headers
- `.github/workflows/lint.yml` — Add endpoint prefix check

---

## Implementation Order

**Week 1 (by Friday)**:
1. ✅ Phase 2 complete & deployed
2. → A1, A2, A3 (architecture type safety) — 3.5h
3. → T4, T5, T6, T7 (ML testing) — 3h

**Week 2 (Monday)**:
4. → A4, A5 (config & scheduling) — 2h
5. → D6, D7, D8, D9, D10 (DevOps) — 3h
6. → C3, C4, C5 (documentation) — 2h
7. → S9-S12 (security) — 1h

---

## Testing Checklist

- [ ] mypy --strict passes on all files
- [ ] ruff check passes (0 errors)
- [ ] pytest coverage >=80% on all modules
- [ ] Type-safe api_client works without `# type: ignore`
- [ ] All API endpoints have response_model
- [ ] ML rule engine has single unified API
- [ ] E2E signal generation test passes
- [ ] Grafana has >=5 alert rules configured
- [ ] nginx logs persist on container restart
- [ ] docker-compose.override.yml.example works for dev

---

## Success Criteria

1. **Code Quality**: All type errors resolved; 0 `# type: ignore` in api_client.py
2. **Test Coverage**: 80%+ on all modules; E2E tests passing
3. **DevOps**: Monitoring alerts functional; logs persistent; CI/CD secrets configured
4. **Documentation**: 3 new guides completed; all processes documented
5. **Security**: All medium-priority issues addressed; rate limit headers implemented

---

## Expected Audit Impact

| Category | Before Phase 3 | After Phase 3 | Change |
|----------|---|---|---|
| Architecture | B- | A- | Type safety, clear boundaries |
| Testing | B- | A- | E2E coverage, regression detection |
| DevOps | A- | A | Monitoring, logging, CI caching |
| Documentation | 90% | 95% | 3 new guides |
| **Overall** | **B+** | **A** | Production-ready |

---

*Next: Begin implementation of A1 (api_client type safety)*
