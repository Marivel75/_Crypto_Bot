# Backend / API Team Context

You are working as the Backend/API agent for crypto-bot.

## Your Scope

- **Code**: `src/api/` only
- **Doc**: `docs/03-backend-api.md`
- **Commit scope**: `api`
- **Do NOT touch**: `src/etl/`, `src/ml/`, `src/frontend/`

## Architecture

```
src/api/
  main.py              # FastAPI app, lifespan, CORS, exception handlers
  routers/             # auth, crypto, signals, news, portfolio, watchlist, chat, system
  services/            # business logic (signal_service, crypto_service, auth_service)
  dependencies.py      # get_db(), get_current_user(), get_signal_service()
  schemas/             # Request/Response Pydantic models (separate from shared models)
```

## Response Envelope (all endpoints)

```python
{
    "success": bool,
    "data": Any | None,
    "error": str | None,
    "meta": {"total": int, "page": int, "limit": int} | None
}
```

## Rules

- Every endpoint must declare a `response_model`
- Use `Depends()` for all service/repo injection
- `HTTPException` for client errors (4xx), log + raise for server errors (5xx)
- Rate-limit auth endpoints (`slowapi`)
- Pagination on all list endpoints (limit/offset, default limit=50, max=200)
- Health check at `GET /api/health`

## Auth

- JWT access token (15 min) + refresh token (7 days)
- `@Depends(get_current_user)` on all protected endpoints
- bcrypt via `passlib[bcrypt]`

## Workflow

1. Read `docs/03-backend-api.md` for full API contract
2. Read `src/shared/models/` for shared domain models
3. Read `src/api/dependencies.py` to understand injection graph
4. Implement in service layer first, then wire up router
5. Write unit tests mocking the service layer
6. Run: `ruff check src/api/ && mypy src/api/ && pytest tests/unit/test_api/ -v`
