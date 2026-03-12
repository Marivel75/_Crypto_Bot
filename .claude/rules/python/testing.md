# Python Testing

## Stack
- **pytest** for all tests
- **pytest-asyncio** for async tests
- **pytest-cov** for coverage (min 80%)
- **factory_boy** for test data generation
- **freezegun** for time mocking

## Test Structure
```python
# test_<module>_<what>_<condition>_<expected>.py
# Inside file: test_<what>_<condition>_<expected>

class TestPositionSizer:
    def test_calculate_size_normal_input_returns_correct_size(self):
        sizer = PositionSizer(account_balance=10000)
        size = sizer.calculate(risk_pct=0.02, entry=100, stop=95)
        assert size == pytest.approx(40.0)

    def test_calculate_size_zero_balance_raises_value_error(self):
        with pytest.raises(ValueError, match="balance"):
            PositionSizer(account_balance=0)
```

## Fixtures
```python
@pytest.fixture
def db_session():
    """Isolated DB session per test."""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def mock_exchange(mocker):
    return mocker.patch("myapp.exchange.client", autospec=True)
```

## Async Tests
```python
@pytest.mark.asyncio
async def test_fetch_data_returns_list():
    result = await fetch_data("https://api.example.com")
    assert isinstance(result, list)
```

## Coverage Gate
```ini
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"
```

## Rules
- No shared mutable state between tests
- Fixed timestamps: `@freeze_time("2025-01-01")`
- Deterministic random: `random.seed(42)` or `np.random.seed(42)` in fixtures
- Mock ALL external APIs — no live network calls in unit tests
