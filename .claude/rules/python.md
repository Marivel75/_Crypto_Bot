# Python Rules (*.py)

## Style
- Use `ruff` for linting and formatting (replaces black, isort, flake8)
- Type hints on ALL function signatures
- Docstrings only on public API functions (Google style)
- Use `logging` module, never `print()`
- Use `pathlib.Path` over `os.path`

## Pydantic
- All data models inherit from `pydantic.BaseModel`
- Use `pydantic-settings` for configuration (reads `.env`)
- Use `Field(...)` with descriptions for API-facing models
- Validators use `@field_validator` (Pydantic v2)

## FastAPI
- Routers in `src/api/routers/`
- Dependencies in `src/api/dependencies.py`
- Response model on every endpoint
- HTTPException for errors with appropriate status codes
- Background tasks for non-blocking operations

## Database
- SQLAlchemy 2.0 async style
- Alembic for migrations
- Connection pooling via SQLAlchemy engine
- TimescaleDB hypertable for time-series data
- Use parameterized queries — NEVER string interpolation for SQL

## Testing
- pytest with fixtures
- Use `pytest-asyncio` for async tests
- Factory pattern for test data
- Mock external APIs (httpx, respx)
- Minimum 80% coverage per module

## Imports Order (ruff handles this)
1. stdlib
2. third-party
3. local (src.*)

## Error Handling
- Custom exception classes in `src/shared/exceptions.py`
- Always log exceptions with context
- Never bare `except:` — catch specific exceptions
- Use `logging.exception()` for unexpected errors
