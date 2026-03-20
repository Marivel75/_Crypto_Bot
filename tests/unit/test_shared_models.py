"""Unit tests for shared Pydantic models and custom exception hierarchy."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
from decimal import Decimal

import pydantic
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
from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord
from src.shared.models.signal import TradingSignal
from src.shared.models.user import UserCreate

_TS = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# OHLCVRecord
# ---------------------------------------------------------------------------


class TestOHLCVRecord:
    def test_valid_creation(self) -> None:
        record = OHLCVRecord(
            symbol="BTC",
            price_open=Decimal("50000.00"),
            price_high=Decimal("51000.00"),
            price_low=Decimal("49500.00"),
            price_close=Decimal("50800.00"),
            volume_24h=Decimal("2500000.00"),
            timestamp=_TS,
            source="binance",
            timeframe="1h",
        )

        assert record.symbol == "BTC"
        assert record.price_open == Decimal("50000.00")
        assert record.price_high == Decimal("51000.00")
        assert record.price_low == Decimal("49500.00")
        assert record.price_close == Decimal("50800.00")
        assert record.volume_24h == Decimal("2500000.00")
        assert record.timestamp == _TS
        assert record.source == "binance"
        assert record.timeframe == "1h"
        # Optional field defaults to None
        assert record.market_cap is None

    def test_valid_creation_with_market_cap(self) -> None:
        record = OHLCVRecord(
            symbol="ETH",
            price_open=Decimal("3000"),
            price_high=Decimal("3100"),
            price_low=Decimal("2950"),
            price_close=Decimal("3050"),
            volume_24h=Decimal("800000"),
            market_cap=Decimal("360000000000"),
            timestamp=_TS,
            source="coingecko",
            timeframe="4h",
        )

        assert record.market_cap == Decimal("360000000000")

    def test_missing_required_field_symbol(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            OHLCVRecord(  # type: ignore[call-arg]
                price_open=Decimal("50000"),
                price_high=Decimal("51000"),
                price_low=Decimal("49000"),
                price_close=Decimal("50500"),
                volume_24h=Decimal("1000000"),
                timestamp=_TS,
                source="binance",
                timeframe="1h",
            )

    def test_missing_required_field_timestamp(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            OHLCVRecord(  # type: ignore[call-arg]
                symbol="BTC",
                price_open=Decimal("50000"),
                price_high=Decimal("51000"),
                price_low=Decimal("49000"),
                price_close=Decimal("50500"),
                volume_24h=Decimal("1000000"),
                source="binance",
                timeframe="1h",
            )

    def test_missing_required_field_source(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            OHLCVRecord(  # type: ignore[call-arg]
                symbol="BTC",
                price_open=Decimal("50000"),
                price_high=Decimal("51000"),
                price_low=Decimal("49000"),
                price_close=Decimal("50500"),
                volume_24h=Decimal("1000000"),
                timestamp=_TS,
                timeframe="1h",
            )

    def test_model_is_frozen(self) -> None:
        record = OHLCVRecord(
            symbol="BTC",
            price_open=Decimal("50000"),
            price_high=Decimal("51000"),
            price_low=Decimal("49000"),
            price_close=Decimal("50500"),
            volume_24h=Decimal("1000000"),
            timestamp=_TS,
            source="binance",
            timeframe="1h",
        )

        with pytest.raises((TypeError, Exception)):
            record.symbol = "ETH"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IndicatorRecord
# ---------------------------------------------------------------------------


class TestIndicatorRecord:
    def test_valid_with_all_fields(self) -> None:
        record = IndicatorRecord(
            symbol="SOL",
            timeframe="4h",
            timestamp=_TS,
            rsi=Decimal("72.3"),
            bollinger_upper=Decimal("155.00"),
            bollinger_middle=Decimal("148.00"),
            bollinger_lower=Decimal("141.00"),
            price_vs_bollinger=Decimal("0.65"),
            harmonic_pattern="Gartley",
            trend_slope=Decimal("0.12"),
            trend_type="aggressive",
            metadata={"custom_key": "custom_value"},
        )

        assert record.symbol == "SOL"
        assert record.rsi == Decimal("72.3")
        assert record.bollinger_upper == Decimal("155.00")
        assert record.bollinger_middle == Decimal("148.00")
        assert record.bollinger_lower == Decimal("141.00")
        assert record.price_vs_bollinger == Decimal("0.65")
        assert record.harmonic_pattern == "Gartley"
        assert record.trend_slope == Decimal("0.12")
        assert record.trend_type == "aggressive"
        assert record.metadata == {"custom_key": "custom_value"}

    def test_valid_with_optional_nulls(self) -> None:
        record = IndicatorRecord(
            symbol="ADA",
            timeframe="1h",
            timestamp=_TS,
        )

        assert record.rsi is None
        assert record.bollinger_upper is None
        assert record.bollinger_middle is None
        assert record.bollinger_lower is None
        assert record.price_vs_bollinger is None
        assert record.harmonic_pattern is None
        assert record.trend_slope is None
        assert record.trend_type is None
        assert record.metadata == {}

    def test_missing_required_field_symbol(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            IndicatorRecord(  # type: ignore[call-arg]
                timeframe="4h",
                timestamp=_TS,
            )

    def test_model_is_frozen(self) -> None:
        record = IndicatorRecord(symbol="ETH", timeframe="1h", timestamp=_TS)

        with pytest.raises((TypeError, Exception)):
            record.rsi = Decimal("50")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NewsArticle
# ---------------------------------------------------------------------------


class TestNewsArticle:
    def test_valid_creation(self) -> None:
        article = NewsArticle(
            title="Bitcoin ETF Approved by SEC",
            source="decrypt",
            url="https://decrypt.co/article/bitcoin-etf",
        )

        assert article.title == "Bitcoin ETF Approved by SEC"
        assert article.source == "decrypt"
        assert article.url == "https://decrypt.co/article/bitcoin-etf"
        assert article.content is None
        assert article.published_at is None
        assert article.sentiment_score is None
        assert article.keywords == []
        assert article.reliability_score is None

    def test_valid_creation_with_all_fields(self) -> None:
        article = NewsArticle(
            title="Ethereum Staking Yields Drop",
            content="Full article body text here.",
            source="cointelegraph",
            url="https://cointelegraph.com/article/eth-staking",
            published_at=_TS,
            sentiment_score=Decimal("-0.45"),
            keywords=["staking", "yield", "ethereum"],
            reliability_score=Decimal("0.82"),
        )

        assert article.sentiment_score == Decimal("-0.45")
        assert article.keywords == ["staking", "yield", "ethereum"]

    def test_sentiment_range_positive_boundary(self) -> None:
        article = NewsArticle(
            title="Huge rally",
            source="news",
            url="https://example.com",
            sentiment_score=Decimal("1.0"),
        )

        assert article.sentiment_score == Decimal("1.0")

    def test_sentiment_range_negative_boundary(self) -> None:
        article = NewsArticle(
            title="Market crash",
            source="news",
            url="https://example.com",
            sentiment_score=Decimal("-1.0"),
        )

        assert article.sentiment_score == Decimal("-1.0")

    def test_sentiment_range_neutral(self) -> None:
        article = NewsArticle(
            title="No change",
            source="news",
            url="https://example.com",
            sentiment_score=Decimal("0.0"),
        )

        assert article.sentiment_score == Decimal("0.0")

    def test_missing_required_field_title(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            NewsArticle(  # type: ignore[call-arg]
                source="decrypt",
                url="https://example.com",
            )


# ---------------------------------------------------------------------------
# TradingSignal
# ---------------------------------------------------------------------------


class TestTradingSignal:
    def test_valid_signal(self) -> None:
        signal = TradingSignal(
            symbol="BTCUSDT",
            signal_type="BUY",
            confidence_score=Decimal("0.85"),
            timeframe_primary="4h",
            model_version="rules_v1",
        )

        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == "BUY"
        assert signal.confidence_score == Decimal("0.85")
        assert signal.timeframe_primary == "4h"
        assert signal.model_version == "rules_v1"
        assert signal.timeframes_aligned == {}
        assert signal.rules_triggered == []
        assert signal.leverage_suggested is None
        assert signal.margin_safety is None
        assert signal.fees_estimated is None
        assert signal.created_at is None

    def test_valid_signal_with_full_fields(self) -> None:
        signal = TradingSignal(
            symbol="ETHUSDT",
            signal_type="SELL",
            confidence_score=Decimal("0.70"),
            timeframe_primary="1h",
            timeframes_aligned={"1h": {"rsi": 75}, "4h": {"rsi": 72}},
            rules_triggered=["rsi_overbought_multi_tf", "bollinger_upper_break"],
            leverage_suggested=5,
            margin_safety=Decimal("0.5"),
            fees_estimated=Decimal("0.002"),
            model_version="xgboost_v2",
            created_at=_TS,
        )

        assert signal.rules_triggered == ["rsi_overbought_multi_tf", "bollinger_upper_break"]
        assert signal.leverage_suggested == 5
        assert signal.created_at == _TS

    def test_confidence_bounds_at_zero(self) -> None:
        signal = TradingSignal(
            symbol="BTCUSDT",
            signal_type="HOLD",
            confidence_score=Decimal("0.0"),
            timeframe_primary="4h",
            model_version="rules_v1",
        )

        assert signal.confidence_score == Decimal("0.0")

    def test_confidence_bounds_at_one(self) -> None:
        signal = TradingSignal(
            symbol="BTCUSDT",
            signal_type="BUY",
            confidence_score=Decimal("1.0"),
            timeframe_primary="4h",
            model_version="rules_v1",
        )

        assert signal.confidence_score == Decimal("1.0")

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TradingSignal(
                symbol="BTCUSDT",
                signal_type="BUY",
                confidence_score=Decimal("1.01"),
                timeframe_primary="4h",
                model_version="rules_v1",
            )

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TradingSignal(
                symbol="BTCUSDT",
                signal_type="BUY",
                confidence_score=Decimal("-0.01"),
                timeframe_primary="4h",
                model_version="rules_v1",
            )

    def test_missing_required_field_symbol(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TradingSignal(  # type: ignore[call-arg]
                signal_type="BUY",
                confidence_score=Decimal("0.8"),
                timeframe_primary="4h",
                model_version="rules_v1",
            )

    def test_model_is_frozen(self) -> None:
        signal = TradingSignal(
            symbol="BTCUSDT",
            signal_type="BUY",
            confidence_score=Decimal("0.8"),
            timeframe_primary="4h",
            model_version="rules_v1",
        )

        with pytest.raises((TypeError, Exception)):
            signal.symbol = "ETHUSDT"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UserCreate
# ---------------------------------------------------------------------------


class TestUserCreate:
    def test_valid_user(self) -> None:
        user = UserCreate(
            username="alice",
            email="alice@example.com",
            password="securepass123",  # noqa: S106
            persona_type="trader",
        )

        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.persona_type == "trader"

    def test_password_too_short(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                username="alice",
                email="alice@example.com",
                password="short",  # noqa: S106 — 5 chars, min is 8
                persona_type="trader",
            )

    def test_valid_email_required(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                username="alice",
                email="not-an-email",
                password="securepass123",  # noqa: S106
                persona_type="trader",
            )

    def test_username_too_short(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                username="ab",  # min_length is 3
                email="alice@example.com",
                password="securepass123",  # noqa: S106
                persona_type="trader",
            )

    def test_username_too_long(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                username="a" * 101,  # max_length is 100
                email="alice@example.com",
                password="securepass123",  # noqa: S106
                persona_type="trader",
            )

    def test_model_is_frozen(self) -> None:
        user = UserCreate(
            username="alice",
            email="alice@example.com",
            password="securepass123",  # noqa: S106
            persona_type="trader",
        )

        with pytest.raises((TypeError, Exception)):
            user.username = "bob"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_not_found_error(self) -> None:
        err = NotFoundError()

        assert err.status_code == 404
        assert err.message == "Resource not found"
        assert err.detail is None
        assert str(err) == "Resource not found"

    def test_not_found_error_custom_message(self) -> None:
        err = NotFoundError("Signal 42 not found", detail={"id": 42})

        assert err.message == "Signal 42 not found"
        assert err.detail == {"id": 42}

    def test_rate_limit_error(self) -> None:
        err = RateLimitError()

        assert err.status_code == 429
        assert err.message == "Rate limit exceeded"
        assert err.detail is None

    def test_rate_limit_error_custom(self) -> None:
        err = RateLimitError("Binance rate limit", detail={"retry_after": 60})

        assert err.message == "Binance rate limit"
        assert err.detail == {"retry_after": 60}

    def test_exception_hierarchy_not_found_is_crypto_bot_error(self) -> None:
        err = NotFoundError()

        assert isinstance(err, CryptoBotError)
        assert isinstance(err, Exception)

    def test_exception_hierarchy_rate_limit_is_external_api(self) -> None:
        err = RateLimitError()

        assert isinstance(err, ExternalAPIError)
        assert isinstance(err, CryptoBotError)

    def test_exception_hierarchy_validation_is_crypto_bot_error(self) -> None:
        err = ValidationError("bad data")

        assert isinstance(err, CryptoBotError)
        assert err.status_code == 422

    def test_exception_hierarchy_authentication(self) -> None:
        err = AuthenticationError()

        assert isinstance(err, CryptoBotError)
        assert err.status_code == 401

    def test_exception_hierarchy_authorization(self) -> None:
        err = AuthorizationError()

        assert isinstance(err, CryptoBotError)
        assert err.status_code == 403

    def test_etl_hierarchy(self) -> None:
        collector_err = CollectorError("collector failed")
        loader_err = LoaderError("load failed")
        transform_err = TransformError("transform failed")
        source_err = DataSourceUnavailable("binance down")

        assert isinstance(collector_err, ETLError)
        assert isinstance(collector_err, CryptoBotError)
        assert isinstance(loader_err, ETLError)
        assert isinstance(transform_err, ETLError)
        assert isinstance(source_err, CollectorError)
        assert isinstance(source_err, ETLError)

    def test_configuration_error(self) -> None:
        err = ConfigurationError("missing DATABASE_URL")

        assert isinstance(err, CryptoBotError)
        assert err.status_code == 500

    def test_crypto_bot_error_repr(self) -> None:
        err = CryptoBotError("test error", detail={"key": "val"})
        r = repr(err)

        assert "CryptoBotError" in r
        assert "test error" in r

    def test_can_raise_and_catch_as_base(self) -> None:
        with pytest.raises(CryptoBotError):
            raise NotFoundError("missing resource")

    def test_can_raise_and_catch_as_base_rate_limit(self) -> None:
        with pytest.raises(ExternalAPIError):
            raise RateLimitError("too many requests")
