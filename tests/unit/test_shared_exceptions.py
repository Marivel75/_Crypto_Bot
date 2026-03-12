"""Unit tests for the shared custom exception hierarchy.

Dedicated test module for src/shared/exceptions.py covering:
- CryptoBotError base class attributes (message, detail, status_code, repr)
- All concrete subclasses with correct status codes
- Exception hierarchy (isinstance checks)
- raise / catch semantics
"""

from __future__ import annotations

import pytest

from src.shared.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CollectorError,
    ConfigurationError,
    CryptoBotError,
    DataSourceUnavailable,
    ETLError,
    ExternalAPIError,
    LoaderError,
    NotFoundError,
    RateLimitError,
    TransformError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# CryptoBotError — base class
# ---------------------------------------------------------------------------


class TestCryptoBotError:
    def test_message_stored(self) -> None:
        err = CryptoBotError("base failure")
        assert err.message == "base failure"

    def test_str_returns_message(self) -> None:
        err = CryptoBotError("base failure")
        assert str(err) == "base failure"

    def test_detail_defaults_to_none(self) -> None:
        err = CryptoBotError("base failure")
        assert err.detail is None

    def test_detail_stored_when_provided(self) -> None:
        err = CryptoBotError("base failure", detail={"key": "value"})
        assert err.detail == {"key": "value"}

    def test_status_code_is_500(self) -> None:
        err = CryptoBotError("base failure")
        assert err.status_code == 500

    def test_repr_contains_class_name(self) -> None:
        err = CryptoBotError("test message")
        assert "CryptoBotError" in repr(err)

    def test_repr_contains_message(self) -> None:
        err = CryptoBotError("test message")
        assert "test message" in repr(err)

    def test_repr_contains_detail(self) -> None:
        err = CryptoBotError("test message", detail={"k": "v"})
        assert "k" in repr(err)

    def test_is_instance_of_exception(self) -> None:
        err = CryptoBotError("test")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(CryptoBotError, match="test"):
            raise CryptoBotError("test")

    def test_detail_can_be_any_type(self) -> None:
        err = CryptoBotError("list detail", detail=[1, 2, 3])
        assert err.detail == [1, 2, 3]

        err2 = CryptoBotError("int detail", detail=42)
        assert err2.detail == 42


# ---------------------------------------------------------------------------
# NotFoundError
# ---------------------------------------------------------------------------


class TestNotFoundError:
    def test_default_message(self) -> None:
        err = NotFoundError()
        assert err.message == "Resource not found"

    def test_default_status_code(self) -> None:
        err = NotFoundError()
        assert err.status_code == 404

    def test_default_detail_is_none(self) -> None:
        err = NotFoundError()
        assert err.detail is None

    def test_custom_message(self) -> None:
        err = NotFoundError("Signal 99 not found")
        assert err.message == "Signal 99 not found"

    def test_custom_detail(self) -> None:
        err = NotFoundError("missing", detail={"id": 99})
        assert err.detail == {"id": 99}

    def test_is_cryptobot_error(self) -> None:
        assert isinstance(NotFoundError(), CryptoBotError)

    def test_can_be_caught_as_base(self) -> None:
        with pytest.raises(CryptoBotError):
            raise NotFoundError("not there")


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------


class TestValidationError:
    def test_default_message(self) -> None:
        err = ValidationError()
        assert err.message == "Validation failed"

    def test_status_code_is_422(self) -> None:
        err = ValidationError()
        assert err.status_code == 422

    def test_custom_message(self) -> None:
        err = ValidationError("symbol must be uppercase")
        assert err.message == "symbol must be uppercase"

    def test_is_cryptobot_error(self) -> None:
        assert isinstance(ValidationError(), CryptoBotError)


# ---------------------------------------------------------------------------
# AuthenticationError
# ---------------------------------------------------------------------------


class TestAuthenticationError:
    def test_default_message(self) -> None:
        err = AuthenticationError()
        assert err.message == "Authentication required"

    def test_status_code_is_401(self) -> None:
        err = AuthenticationError()
        assert err.status_code == 401

    def test_custom_message(self) -> None:
        err = AuthenticationError("token expired")
        assert err.message == "token expired"

    def test_is_cryptobot_error(self) -> None:
        assert isinstance(AuthenticationError(), CryptoBotError)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("bad credentials")


# ---------------------------------------------------------------------------
# AuthorizationError
# ---------------------------------------------------------------------------


class TestAuthorizationError:
    def test_default_message(self) -> None:
        err = AuthorizationError()
        assert err.message == "Access forbidden"

    def test_status_code_is_403(self) -> None:
        err = AuthorizationError()
        assert err.status_code == 403

    def test_is_cryptobot_error(self) -> None:
        assert isinstance(AuthorizationError(), CryptoBotError)

    def test_custom_detail(self) -> None:
        err = AuthorizationError("forbidden", detail={"resource": "portfolio"})
        assert err.detail == {"resource": "portfolio"}


# ---------------------------------------------------------------------------
# ExternalAPIError
# ---------------------------------------------------------------------------


class TestExternalAPIError:
    def test_default_message(self) -> None:
        err = ExternalAPIError()
        assert err.message == "External API error"

    def test_status_code_is_502(self) -> None:
        err = ExternalAPIError()
        assert err.status_code == 502

    def test_is_cryptobot_error(self) -> None:
        assert isinstance(ExternalAPIError(), CryptoBotError)

    def test_custom_message_and_detail(self) -> None:
        err = ExternalAPIError("Binance unreachable", detail="connect timeout")
        assert err.message == "Binance unreachable"
        assert err.detail == "connect timeout"


# ---------------------------------------------------------------------------
# RateLimitError
# ---------------------------------------------------------------------------


class TestRateLimitError:
    def test_default_message(self) -> None:
        err = RateLimitError()
        assert err.message == "Rate limit exceeded"

    def test_status_code_is_429(self) -> None:
        err = RateLimitError()
        assert err.status_code == 429

    def test_is_external_api_error(self) -> None:
        assert isinstance(RateLimitError(), ExternalAPIError)

    def test_is_cryptobot_error(self) -> None:
        assert isinstance(RateLimitError(), CryptoBotError)

    def test_can_be_caught_as_external_api_error(self) -> None:
        with pytest.raises(ExternalAPIError):
            raise RateLimitError("too many requests")

    def test_detail_carries_retry_after(self) -> None:
        err = RateLimitError("Binance rate limit", detail={"retry_after": "30"})
        assert err.detail == {"retry_after": "30"}


# ---------------------------------------------------------------------------
# ETL hierarchy
# ---------------------------------------------------------------------------


class TestETLHierarchy:
    def test_etl_error_is_cryptobot_error(self) -> None:
        err = ETLError("etl failed")
        assert isinstance(err, CryptoBotError)
        assert err.status_code == 500

    def test_collector_error_is_etl_error(self) -> None:
        err = CollectorError("collector failed")
        assert isinstance(err, ETLError)
        assert isinstance(err, CryptoBotError)

    def test_data_source_unavailable_is_collector_error(self) -> None:
        err = DataSourceUnavailable("binance down")
        assert isinstance(err, CollectorError)
        assert isinstance(err, ETLError)
        assert isinstance(err, CryptoBotError)

    def test_loader_error_is_etl_error(self) -> None:
        err = LoaderError("db write failed")
        assert isinstance(err, ETLError)
        assert isinstance(err, CryptoBotError)

    def test_transform_error_is_etl_error(self) -> None:
        err = TransformError("bad indicator data")
        assert isinstance(err, ETLError)
        assert isinstance(err, CryptoBotError)

    def test_collector_error_can_be_caught_as_etl_error(self) -> None:
        with pytest.raises(ETLError):
            raise CollectorError("collector failure")

    def test_loader_error_message(self) -> None:
        err = LoaderError("failed to insert 42 records")
        assert err.message == "failed to insert 42 records"

    def test_transform_error_with_detail(self) -> None:
        err = TransformError("rsi computation failed", detail={"symbol": "BTCUSDT"})
        assert err.detail == {"symbol": "BTCUSDT"}


# ---------------------------------------------------------------------------
# ConfigurationError
# ---------------------------------------------------------------------------


class TestConfigurationError:
    def test_is_cryptobot_error(self) -> None:
        err = ConfigurationError("missing DATABASE_URL")
        assert isinstance(err, CryptoBotError)

    def test_status_code_is_500(self) -> None:
        err = ConfigurationError("bad config")
        assert err.status_code == 500

    def test_message_stored(self) -> None:
        err = ConfigurationError("MINIO_ENDPOINT not set")
        assert err.message == "MINIO_ENDPOINT not set"
