# Backend / API Rules

## Scope: `src/api/`

## FastAPI
- App entry point: `src/api/main.py`
- Routers in `src/api/routers/` (auth, crypto, signals, news, portfolio, watchlist, chat, system)
- Services in `src/api/services/` (business logic separated from routes)
- Dependencies in `src/api/dependencies.py` (DB session, current_user)
- CORS configured for Streamlit frontend origin

## Auth
- bcrypt for password hashing
- JWT tokens (access + refresh)
- `@Depends(get_current_user)` on protected endpoints
- No session-based auth

## API Response Format
```python
{
    "success": bool,
    "data": Any | None,
    "error": str | None,
    "meta": {"total": int, "page": int, "limit": int} | None
}
```

## Endpoints
- All endpoints return typed Pydantic response models
- Pagination on list endpoints (limit/offset)
- Rate limiting on auth endpoints
- Health check at `/api/health`

## DO NOT
- Access TimescaleDB directly for ETL operations
- Import from `src/etl/`, `src/ml/`, `src/frontend/`
- Expose internal error details to clients
- Store passwords in plain text
