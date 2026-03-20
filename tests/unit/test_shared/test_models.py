"""Unit tests for shared Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
from decimal import Decimal

import pydantic
import pytest

from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord
from src.shared.models.signal import SignalOutcome, TradingSignal
from src.shared.models.user import UserCreate, UserRead

TEST_TS = datetime(2025, 1, 1, tzinfo=UTC)
DUMMY_CRED = "x" * 10  # noqa: S105


class TestOHLCVRecord:
    def test_valid(self) -> None:
        record = OHLCVRecord(
            symbol="BTC",
            price_open=Decimal("50000"),
            price_high=Decimal("51000"),
            price_low=Decimal("49000"),
            price_close=Decimal("50500"),
            volume_24h=Decimal("1000000"),
            timestamp=TEST_TS,
            source="binance",
            timeframe="1h",
        )
        assert record.symbol == "BTC"
        assert record.market_cap is None


class TestIndicatorRecord:
    def test_valid_minimal(self) -> None:
        record = IndicatorRecord(
            symbol="ETH",
            timeframe="4h",
            timestamp=TEST_TS,
        )
        assert record.rsi is None
        assert record.metadata == {}

    def test_valid_full(self) -> None:
        record = IndicatorRecord(
            symbol="ETH",
            timeframe="4h",
            timestamp=TEST_TS,
            rsi=Decimal("65.5"),
            bollinger_upper=Decimal("3500"),
            bollinger_middle=Decimal("3400"),
            bollinger_lower=Decimal("3300"),
        )
        assert record.rsi == Decimal("65.5")


class TestNewsArticle:
    def test_valid(self) -> None:
        article = NewsArticle(
            title="Bitcoin hits new high",
            source="decrypt",
            url="https://example.com/article",
        )
        assert article.keywords == []
        assert article.sentiment_score is None


class TestTradingSignal:
    def test_valid(self) -> None:
        signal = TradingSignal(
            symbol="BTCUSDT",
            signal_type="BUY",
            confidence_score=Decimal("0.75"),
            timeframe_primary="4h",
            model_version="rules_v1",
        )
        assert signal.rules_triggered == []
        assert signal.leverage_suggested is None

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TradingSignal(
                symbol="BTC",
                signal_type="BUY",
                confidence_score=Decimal("1.5"),
                timeframe_primary="4h",
                model_version="rules_v1",
            )


class TestSignalOutcome:
    def test_valid(self) -> None:
        outcome = SignalOutcome(
            signal_id="abc123",
            price_at_signal=Decimal("50000"),
            evaluated_at=TEST_TS,
        )
        assert outcome.was_correct is None


class TestUserCreate:
    def test_valid(self) -> None:
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password=DUMMY_CRED,
            persona_type="trader",
        )
        assert user.username == "testuser"

    def test_username_too_short(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                username="ab",
                email="test@example.com",
                password=DUMMY_CRED,
                persona_type="trader",
            )

    def test_short_credential(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="short",  # noqa: S105, S106
                persona_type="trader",
            )


class TestUserRead:
    def test_valid(self) -> None:
        user = UserRead(
            id="123",
            username="test",
            email="test@example.com",
            persona_type="trader",
            created_at=TEST_TS,
        )
        assert user.preferences == {}
