# Testing Standards

## Coverage
- Minimum 80% code coverage
- Coverage gate in CI (`--cov-fail-under=80`)

## Methodology
- TDD: write tests first, then implement
- Each requirement maps to at least one test case
- Tests are requirement-driven, not implementation-driven

## Test Types
- **Unit**: no I/O, no network, no database. Fast and isolated.
- **Integration**: with Docker services (database, Redis, etc.)
- **E2E**: full stack, simulating real user flows

## Practices
- Mock all external APIs (exchanges, third-party services)
- Use fixed timestamps in tests (never `datetime.now()` in assertions)
- Deterministic random seeds for ML tests
- Factory pattern for test data creation
- Each test independent: no shared mutable state

## Required Scenarios
1. Happy path: all normal use cases
2. Edge cases: boundary values, empty inputs, max limits
3. Error handling: invalid inputs, failures, permissions
4. State transitions: all valid state changes (if stateful)

## Naming
Format: `test_<what>_<condition>_<expected>`
Example: `test_position_size_exceeds_limit_raises_error`
