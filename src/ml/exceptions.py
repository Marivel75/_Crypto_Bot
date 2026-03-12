"""ML module exceptions.

All ML-specific exceptions inherit from ``MLBaseException``, which itself
inherits from the project-wide ``CryptoBotError`` so that FastAPI handlers
can catch them uniformly.
"""

from __future__ import annotations

from typing import Any

from src.shared.exceptions import CryptoBotError


class MLBaseException(CryptoBotError):
    """Base exception for all ML module errors."""

    def __init__(self, message: str = "ML error", detail: Any = None) -> None:
        super().__init__(message=message, detail=detail)


class InsufficientDataError(MLBaseException):
    """Not enough data points to compute indicators or train a model."""

    def __init__(
        self,
        message: str = "Insufficient data for computation",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class ModelNotFoundError(MLBaseException):
    """Requested ML model not found in MLflow registry."""

    status_code: int = 404

    def __init__(
        self,
        message: str = "Model not found in registry",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class SignalRejectedError(MLBaseException):
    """Signal failed validation (confidence, fees, margin)."""

    def __init__(
        self,
        message: str = "Signal rejected by validation gate",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)


class ConfigurationError(MLBaseException):
    """Invalid or missing ML configuration."""

    def __init__(
        self,
        message: str = "ML configuration error",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, detail=detail)
