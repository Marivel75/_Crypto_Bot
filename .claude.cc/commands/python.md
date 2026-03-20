# Python Quality Checks

Run the full Python quality gate for crypto-bot.

## Steps

1. Lint with auto-fix: `cd /Users/amaury/Desktop/jules/crypto-bot && ruff check src/ --fix`
2. Format: `ruff format src/`
3. Type check: `mypy src/ --ignore-missing-imports`
4. Security scan: `ruff check src/ --select=S`
5. Run tests with coverage: `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`
6. Report any issues that could not be auto-fixed

## Quick Reference

| Tool | Command | Purpose |
|------|---------|---------|
| ruff | `ruff check src/ --fix` | Lint + isort + bugbear |
| ruff | `ruff format src/` | Format (replaces black) |
| mypy | `mypy src/` | Strict type checking |
| pytest | `pytest tests/ -v` | Run all tests |
| pytest | `pytest tests/unit/ -v` | Unit tests only |
| pytest | `pytest tests/ --cov=src --cov-fail-under=80` | With coverage |
| pytest | `pytest tests/ -k "test_name"` | Run specific test |
| pytest | `pytest tests/ -x --tb=short` | Stop on first failure |

## Pre-commit Checklist

- [ ] `ruff check src/` — zero errors
- [ ] `ruff format src/ --check` — no formatting changes needed
- [ ] `mypy src/` — zero type errors
- [ ] `pytest --cov-fail-under=80` — coverage >= 80%
- [ ] No `print()` statements (`ruff check --select=T20`)
- [ ] No hardcoded secrets (`ruff check --select=S105,S106`)
