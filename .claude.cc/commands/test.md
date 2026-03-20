# Run Tests

Run the full test suite for crypto-bot.

## Steps
1. Run unit tests: `cd /Users/amaury/Desktop/jules/crypto-bot && pytest tests/unit/ -v --tb=short`
2. Run integration tests: `pytest tests/integration/ -v --tb=short`
3. Generate coverage report: `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`
4. Report results summary
