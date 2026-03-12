"""Unit tests for shared exceptions."""

from __future__ import annotations

from src.shared.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CryptoBotError,
    ExternalAPIError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


class TestCryptoBotError:
    def test_base_error(self) -> None:
        err = CryptoBotError("something failed", detail={"key": "val"})
        assert err.message == "something failed"
        assert err.detail == {"key": "val"}
        assert err.status_code == 500
        assert str(err) == "something failed"

    def test_repr(self) -> None:
        err = CryptoBotError("test")
        assert "CryptoBotError" in repr(err)


class TestSpecificErrors:
    def test_not_found(self) -> None:
        err = NotFoundError()
        assert err.status_code == 404
        assert err.message == "Resource not found"

    def test_validation(self) -> None:
        err = ValidationError("bad input")
        assert err.status_code == 422

    def test_authentication(self) -> None:
        err = AuthenticationError()
        assert err.status_code == 401

    def test_authorization(self) -> None:
        err = AuthorizationError()
        assert err.status_code == 403

    def test_external_api(self) -> None:
        err = ExternalAPIError("timeout")
        assert err.status_code == 502

    def test_rate_limit(self) -> None:
        err = RateLimitError()
        assert err.status_code == 429
        assert isinstance(err, ExternalAPIError)
