"""Custom exception hierarchy for the crypto-bot application.

Every exception carries a human-readable ``message`` and an optional
``detail`` payload for structured context. HTTP-facing exceptions also
expose a ``status_code`` class attribute so FastAPI exception handlers
can map them to the correct response code without importing FastAPI here.
"""

from __future__ import annotations

from typing import Any


class CryptoBotError(Exception):
    """Base exception for all crypto-bot application errors."""

    status_code: int = 500

    def __init__(self, message: str, detail: Any = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, detail={self.detail!r})"


class NotFoundError(CryptoBotError):
    """Raised when a requested resource does not exist (HTTP 404)."""

    status_code: int = 404

    def __init__(
        self,
        message: str = "Resource not found",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class ValidationError(CryptoBotError):
    """Raised when input data fails validation rules (HTTP 422)."""

    status_code: int = 422

    def __init__(
        self,
        message: str = "Validation failed",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class AuthenticationError(CryptoBotError):
    """Raised when authentication credentials are missing or invalid (HTTP 401)."""

    status_code: int = 401

    def __init__(
        self,
        message: str = "Authentication required",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class AuthorizationError(CryptoBotError):
    """Raised when the authenticated user lacks permission (HTTP 403)."""

    status_code: int = 403

    def __init__(
        self,
        message: str = "Access forbidden",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class ExternalAPIError(CryptoBotError):
    """Raised when an upstream external API call fails (HTTP 502)."""

    status_code: int = 502

    def __init__(
        self,
        message: str = "External API error",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class RateLimitError(ExternalAPIError):
    """Raised when an external API returns a rate-limit response (HTTP 429)."""

    status_code: int = 429

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


# ---------------------------------------------------------------------------
# ETL-specific exceptions
# ---------------------------------------------------------------------------


class ETLError(CryptoBotError):
    """Base exception for ETL pipeline errors."""

    status_code: int = 500


class CollectorError(ETLError):
    """Raised when a data collector encounters an unrecoverable error."""


class DataSourceUnavailable(CollectorError):
    """Raised when an external data source is completely unavailable."""


class LoaderError(ETLError):
    """Raised when data loading into storage fails."""


class TransformError(ETLError):
    """Raised when data transformation or indicator computation fails."""


class ConflictError(CryptoBotError):
    """Raised when a resource already exists or violates a uniqueness constraint (HTTP 409)."""

    status_code: int = 409

    def __init__(
        self,
        message: str = "Resource already exists",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class ConfigurationError(CryptoBotError):
    """Raised when application configuration is invalid or missing."""

    status_code: int = 500
