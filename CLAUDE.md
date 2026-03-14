# Crypto Bot — Claude Code Instructions

## Project Overview

Crypto Bot is a school project: a crypto market surveillance, analytics, and trading signal platform. It is strictly informational — **NO automated trade execution**.

Stack: Python 3.11+ | FastAPI | Streamlit | Plotly | TimescaleDB | MinIO | MLflow | DVC | Docker Compose | Nginx | GitHub Actions

## Architecture

```
[Binance/CoinGecko/CCXT] -> [ETL Python + APScheduler] -> [TimescaleDB + MinIO]
                                                            |
                                              [ML Engine] --+-- [FastAPI REST API]
                                              [Rules+ML]         |
                                              [MLflow]      [Streamlit + Plotly]
```

## Team Boundaries (CRITICAL — never cross these)

| Team | Code directory | Doc | Scopes |
|------|----------------|-----|--------|
| Data Engineering | `src/etl/`, `src/shared/` | `docs/01-data-engineering.md` | `etl`, `shared` |
| ML / Data Science | `src/ml/` | `docs/02-ml-data-science.md` | `ml` |
| Backend / API | `src/api/` | `docs/03-backend-api.md` | `api` |
| Frontend / UI | `src/frontend/` | `docs/04-frontend-ui.md` | `frontend` |
| DevOps / Infra | `infra/`, `docker-compose.yml`, `nginx/` | `docs/05-devops-infra.md` | `infra` |

**NEVER modify code outside your team's directory.** Communicate across teams via shared interfaces in `src/shared/`.

## Python Conventions

Python 3.11+ — modern syntax (`X | Y` unions, `match`, `asyncio.timeout`). See global `~/.claude/rules/python.md` for full style rules.

### Quality Gates (run before every commit)
```bash
ruff check src/ --fix && ruff format src/ && mypy src/ && pytest tests/ --cov=src --cov-fail-under=80
```

## File Organization

```
src/
  etl/          # Data Engineering: collectors, schedulers, loaders
  ml/           # ML: rule engine, models, backtesting, MLflow
  api/          # Backend: FastAPI routers, services, dependencies
  frontend/     # UI: Streamlit pages, components, api_client
  shared/       # Cross-team: models/, config.py, exceptions.py, constants.py
tests/
  unit/         # Pure logic, no I/O
  integration/  # Requires Docker Compose services
  e2e/          # Full-stack critical user flows
docs/           # Team documentation
infra/          # Ansible, CI/CD
```

## Key Files

- `src/shared/config.py` — Centralized `pydantic-settings` config (single source of truth)
- `src/shared/models/` — Shared Pydantic models: `CryptoRecord`, `Signal`, `User`
- `src/shared/exceptions.py` — Custom exception hierarchy
- `.env.example` — Template for all required environment variables
- `pyproject.toml` — Tool configuration (ruff, mypy, pytest, coverage)
- `docs/00-overview.md` — Full project overview (read by ALL teams first)
- `docs/06-roadmap.md` — Sprint planning and KPIs

## Git Workflow

See global `~/.claude/rules/common.md` for full git conventions.

Scopes for this project: `etl`, `ml`, `api`, `frontend`, `infra`, `shared`
Branch format: `team/feature-name` (e.g. `data-eng/binance-collector`, `ml/rsi-multi-tf`)
PR required for `main`, all quality gates must pass.

## Testing

See global `~/.claude/rules/common.md` and `python.md` for full testing rules. Project-specific: mock with `respx`, E2E covers signal generation → API → UI.

## Security

See global rules. Project-specific: bcrypt for passwords, JWT for sessions, signals are read-only (no trade execution).

## Data Sources (free only)

- Binance public REST + WebSocket (OHLCV, order book)
- CoinGecko Demo API (market data, metadata)
- CCXT (fallback multi-exchange)
- News RSS: Decrypt, Cointelegraph, PhoenixNews
- Alternative.me (Fear & Greed Index)
- ESMA, SEC (regulatory)

## Tracked Symbols

Top 30 by market cap. Priority 13: BTC, ETH, USDT, USDC, BNB, XRP, SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM

## Signal Format

```python
{
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "direction": "BUY | SELL | HOLD",
    "confidence": 0.0 - 1.0,        # emit only if >= 0.6
    "entry_price": float,
    "stop_loss": float,
    "take_profit": list[float],
    "leverage_suggested": int,        # always verify 2x margin rule
    "indicators_used": list[str],
    "timestamp": datetime,
}
```

## ML Approach

**Phase 1** — Rule-based engine:
- RSI multi-timeframe convergence (1h, 2h, 3h, 4h)
- Bollinger Bands (squeeze detection, band walking)
- Harmonic patterns (bat, gartley, butterfly, crab)
- Trend lines (weekly stable, monthly aggressive)

**Phase 2** — Supervised ML learning Phase 1 patterns:
- Models: XGBoost, LightGBM, LSTM
- Predict direction/returns — NEVER absolute prices
- Walk-forward backtesting with purging + embargo windows
- MLflow for experiment tracking, DVC for dataset versioning

## Docker Services

`timescaledb` | `minio` | `mlflow` | `api` | `frontend` | `etl-worker` | `nginx`

```bash
cp .env.example .env
docker-compose up -d
```

## Key Technical Decisions (ADRs)

- **TimescaleDB** over vanilla PostgreSQL — time-series hypertables, compression, retention policies
- **MinIO** for S3-compatible object storage — models, datasets, MLflow artifacts
- **No MongoDB** — JSONB columns in PostgreSQL for unstructured data
- **No message broker** — APScheduler + cron Docker for V1
- **Streamlit** over Dash — faster development, native Plotly support
- **No Kubernetes** — Docker Compose for V1, Ansible for VPS provisioning
- **Free data sources only** — no paid exchange subscriptions

## Agent Workflow (Claude Code + ECC)

When starting work on this project:
1. Read `docs/00-overview.md` for full context
2. Read your team's specific doc (`docs/0X-*.md`)
3. Read `src/shared/` to understand shared interfaces
4. Load your team's slash command: `/backend`, `/data-engineering`, `/ml`, `/frontend`, `/devops`
5. Work ONLY within your team's directory
6. Run quality gates before committing: `ruff check && mypy && pytest`

### Project Agents (`.claude/agents/`)

| Agent | File | Scope |
|-------|------|-------|
| Data Engineer | `data-engineer.md` | `src/etl/`, `src/shared/` |
| ML Engineer | `ml-engineer.md` | `src/ml/` |
| Backend Engineer | `backend-engineer.md` | `src/api/` |
| Frontend Engineer | `frontend-engineer.md` | `src/frontend/` |
| DevOps Engineer | `devops-engineer.md` | `infra/`, `docker-compose.yml`, `nginx/`, `.github/` |
| Orchestrator | `orchestrator.md` | Cross-team coordination |

Use the Agent tool with these specialized agents for team-scoped work. For cross-team changes, use the orchestrator agent.

### Global ECC Agents (auto-available)

- `python-reviewer` — Python code review (PEP 8, type hints, security)
- `security-reviewer` — OWASP Top 10, secrets, injection
- `tdd-guide` — Test-driven development enforcement
- `planner` — Complex feature planning
- `database-reviewer` — PostgreSQL/TimescaleDB optimization
- `build-error-resolver` — Fix build/lint errors
- `code-reviewer` — General code quality review

### Available Slash Commands
- `/lint` — run ruff + mypy
- `/test` — run full test suite with coverage
- `/deploy` — deploy to VPS via Ansible
- `/db-migrate` — create and apply Alembic migrations
- `/backend` — Backend/API team context
- `/data-engineering` — Data Engineering team context
- `/ml` — ML/Data Science team context
- `/frontend` — Frontend/UI team context
- `/devops` — DevOps/Infra team context
- `/python-review` — Python code review (ECC)
- `/security-review` — Security audit (ECC)
- `/tdd` — Test-driven development workflow (ECC)
- `/plan` — Feature implementation planning (ECC)

## Pre-Completion Checklist

- [ ] No hardcoded secrets
- [ ] No `print()` statements
- [ ] `ruff check src/` passes
- [ ] `mypy src/` passes
- [ ] `pytest --cov-fail-under=80` passes
- [ ] Code stays within team boundary
- [ ] Commit follows `type(scope): description`
