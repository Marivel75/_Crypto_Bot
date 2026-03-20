# Lint and Type Check

Run all code quality checks on the crypto-bot codebase.

## Steps
1. Run ruff linter: `cd /Users/amaury/Desktop/jules/crypto-bot && ruff check src/ --fix`
2. Run ruff formatter: `ruff format src/`
3. Run mypy type checker: `mypy src/ --ignore-missing-imports`
4. Report any remaining issues
