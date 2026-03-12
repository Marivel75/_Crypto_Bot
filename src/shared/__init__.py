"""Shared foundation — re-exports the most commonly used public interfaces."""

from __future__ import annotations

from src.shared.database import Base, async_engine, async_session_factory, get_db
from src.shared.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CryptoBotError,
    ExternalAPIError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

__all__ = [
    # database
    "Base",
    "async_engine",
    "async_session_factory",
    "get_db",
    # exceptions
    "CryptoBotError",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ExternalAPIError",
    "RateLimitError",
]
