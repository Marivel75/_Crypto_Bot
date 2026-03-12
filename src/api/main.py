"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.routers import (
    auth,
    chat,
    crypto,
    news,
    portfolio,
    signals,
    system,
    watchlist,
)
from src.api.schemas import ApiResponse, ErrorDetail
from src.shared.config import settings
from src.shared.exceptions import CryptoBotError

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Log startup and shutdown events."""
    logger.info(
        "Crypto Bot API starting — host=%s port=%d",
        settings.api_host,
        settings.api_port,
    )
    yield
    logger.info("Crypto Bot API shutting down")


app = FastAPI(
    title="CryptoBot API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS — Restrictive by default (S5 audit fix)
# Only allow configured origins; explicitly list methods; deny Access-Control-Allow-Headers: *
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Total-Count"],
    max_age=3600,
)


# Prometheus metrics
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# Exception handlers
@app.exception_handler(CryptoBotError)
async def cryptobot_error_handler(request: Request, exc: CryptoBotError) -> JSONResponse:
    """Handle all CryptoBotError subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            error=ErrorDetail(
                code=exc.__class__.__name__,
                message=exc.message,
            )
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Wrap Pydantic / FastAPI 422 validation errors in the ApiResponse envelope."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Validation error") if errors else "Validation error"
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=first_msg,
            )
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors without leaking internals."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            )
        ).model_dump(mode="json"),
    )


# Mount routers
app.include_router(system.health_router)
app.include_router(system.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(crypto.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
