"""Unit tests for shared constants."""

from __future__ import annotations

from decimal import Decimal

from src.shared.constants import (
    BINANCE_RATE_LIMIT,
    COINGECKO_RATE_LIMIT,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    PERSONA_TYPES,
    SIGNAL_CONFIDENCE_THRESHOLD,
    SIGNAL_TYPES,
    TIMEFRAMES,
    TRACKED_SYMBOLS,
)


class TestConstants:
    def test_tracked_symbols(self) -> None:
        assert "BTCUSDT" in TRACKED_SYMBOLS
        assert "ETHUSDT" in TRACKED_SYMBOLS
        assert all(s.endswith("USDT") or s.endswith("USDC") for s in TRACKED_SYMBOLS)

    def test_timeframes(self) -> None:
        assert "1h" in TIMEFRAMES
        assert "4h" in TIMEFRAMES

    def test_rate_limits(self) -> None:
        assert BINANCE_RATE_LIMIT == 1200
        assert COINGECKO_RATE_LIMIT == 30

    def test_signal_threshold(self) -> None:
        assert Decimal("0.6") == SIGNAL_CONFIDENCE_THRESHOLD

    def test_signal_types(self) -> None:
        assert set(SIGNAL_TYPES) == {"BUY", "SELL", "HOLD"}

    def test_persona_types(self) -> None:
        assert set(PERSONA_TYPES) == {"trader", "journalist", "investor"}

    def test_pagination(self) -> None:
        assert DEFAULT_PAGE_SIZE == 20
        assert MAX_PAGE_SIZE == 100
