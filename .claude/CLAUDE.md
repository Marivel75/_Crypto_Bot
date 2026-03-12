# Project-Level Agent Instructions — Crypto Bot

This file provides agent-specific orchestration rules for the crypto-bot project.
It supplements the root `CLAUDE.md` and the global `~/.claude/CLAUDE.md`.

## Agent Initialization Protocol

When starting any session in this project:

1. Read root `CLAUDE.md` — project architecture, team boundaries, conventions
2. Read `docs/00-overview.md` — full product vision and feature list
3. Identify which team you are acting for (ETL, ML, API, Frontend, DevOps)
4. Load the corresponding slash command: `/backend`, `/data-engineering`, `/ml`, `/frontend`, `/devops`
5. Read the team's doc (`docs/0X-*.md`) before writing any code
6. Read `src/shared/` to understand shared interfaces and models

## Rule Loading

The following rule files apply to this project (loaded automatically by ECC):

- `~/.claude/rules/common/coding-style.md` — immutability, error handling, file size
- `~/.claude/rules/common/git-workflow.md` — commit format, PR process
- `~/.claude/rules/common/testing.md` — TDD, 80% coverage
- `~/.claude/rules/common/security.md` — secrets, input validation
- `~/.claude/rules/common/patterns.md` — repository pattern, API envelope
- `~/.claude/rules/common/agents.md` — when to delegate to sub-agents
- `~/.claude/rules/python/coding-style.md` — Python-specific: type hints, logging, async
- `~/.claude/rules/python/testing.md` — pytest patterns, respx, asyncio
- `~/.claude/rules/python/patterns.md` — Repository, Service, Collector patterns
- `~/.claude/rules/python/security.md` — SQL injection, bcrypt, JWT, Pydantic validation
- `~/.claude/rules/python/performance.md` — async I/O, connection pooling, batching

Project-scoped rules (in `.claude/rules/`):
- `backend.md` — FastAPI patterns, response envelope, auth
- `data-engineering.md` — ETL pipeline, TimescaleDB, MinIO
- `ml.md` — Rule engine, supervised ML, MLflow, backtesting
- `frontend.md` — Streamlit, Plotly, api_client isolation
- `devops.md` — Docker, Nginx, Ansible, CI/CD
- `python.md` — Python style, Pydantic, async, SQL safety

## Agent Orchestration

### For complex features spanning multiple teams

Use parallel sub-agents:
```
Launch in parallel:
1. ETL agent: implement data collection for new symbol
2. API agent: implement new endpoint returning the data
3. Frontend agent: implement new chart widget
```

### For code review

After writing code, immediately use the `code-reviewer` agent pattern:
- Check for team boundary violations
- Verify Pydantic models are used at boundaries
- Verify no `print()` statements
- Verify no hardcoded values

### For debugging

- ETL issues: check logs with `docker-compose logs etl-worker`
- DB issues: connect via `docker-compose exec timescaledb psql -U postgres`
- API issues: check `GET /api/health`, then specific endpoint logs
- ML issues: check MLflow UI at `http://localhost:5000`

## Quality Gates (enforced by hooks)

After every Python file edit, the hook runs:
```bash
ruff check --select=T20,S105,S106,E9,F401 <file>
```

This catches immediately:
- `print()` statements (T20)
- Hardcoded passwords (S105, S106)
- Syntax errors (E9)
- Unused imports (F401)

Before committing, always run the full gate via `/python`.

## Project-Specific Constraints

- **No paid APIs** — Binance public, CoinGecko Demo, CCXT only
- **No Kubernetes** — Docker Compose for V1
- **No automated trading** — signals are informational only
- **No MongoDB** — use JSONB in TimescaleDB instead
- **No `print()`** — use `logging` module
- **No random train/test splits on time-series** — always temporal
- **Confidence threshold**: only emit signals with `confidence >= 0.6`
