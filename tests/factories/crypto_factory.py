"""Test factories for crypto Pydantic models.

Provides helper functions that return realistic OHLCVRecord and
IndicatorRecord instances with fixed timestamps (never datetime.now()).

Aliases ``OHLCVRecordFactory`` and ``IndicatorRecordFactory`` are provided
for import compatibility with the package ``__init__.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from src.shared.models.crypto import IndicatorRecord, OHLCVRecord

# Fixed reference timestamp — 2024-01-15 08:00 UTC (a real trading session)
_FIXED_TS = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)


def make_ohlcv(**overrides: object) -> OHLCVRecord:
    """Return an OHLCVRecord with realistic BTC candle defaults.

    Args:
        **overrides: Any OHLCVRecord field to override.

    Returns:
        A frozen OHLCVRecord instance.
    """
    defaults: dict[str, object] = {
        "symbol": "BTCUSDT",
        "price_open": Decimal("42000.00"),
        "price_high": Decimal("42850.00"),
        "price_low": Decimal("41750.00"),
        "price_close": Decimal("42500.00"),
        "volume_24h": Decimal("18500.50000000"),
        "market_cap": Decimal("831250000000.00"),
        "timestamp": _FIXED_TS,
        "source": "binance",
        "timeframe": "4h",
    }
    defaults.update(overrides)
    return OHLCVRecord(**defaults)  # type: ignore[arg-type]


def make_ohlcv_eth(**overrides: object) -> OHLCVRecord:
    """Return an OHLCVRecord pre-configured for ETH.

    Args:
        **overrides: Any OHLCVRecord field to override.

    Returns:
        A frozen OHLCVRecord instance.
    """
    eth_defaults: dict[str, object] = {
        "symbol": "ETHUSDT",
        "price_open": Decimal("2250.00"),
        "price_high": Decimal("2310.00"),
        "price_low": Decimal("2215.00"),
        "price_close": Decimal("2285.00"),
        "volume_24h": Decimal("9200.12000000"),
        "market_cap": Decimal("274200000000.00"),
        "timestamp": _FIXED_TS,
        "source": "binance",
        "timeframe": "4h",
    }
    eth_defaults.update(overrides)
    return OHLCVRecord(**eth_defaults)  # type: ignore[arg-type]


def make_indicator(**overrides: object) -> IndicatorRecord:
    """Return an IndicatorRecord with realistic RSI + Bollinger defaults.

    RSI of 68 places price near (but not yet above) the 70 overbought threshold.
    Bollinger values are consistent with BTC at ~42 500 USDT.

    Args:
        **overrides: Any IndicatorRecord field to override.

    Returns:
        A frozen IndicatorRecord instance.
    """
    defaults: dict[str, object] = {
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "timestamp": _FIXED_TS,
        "rsi": Decimal("68.0000"),
        "bollinger_upper": Decimal("43800.00000000"),
        "bollinger_middle": Decimal("42000.00000000"),
        "bollinger_lower": Decimal("40200.00000000"),
        "price_vs_bollinger": Decimal("0.3125"),
        "harmonic_pattern": None,
        "trend_slope": Decimal("0.002500"),
        "trend_type": "stable",
        "metadata": {},
    }
    defaults.update(overrides)
    return IndicatorRecord(**defaults)  # type: ignore[arg-type]


def make_indicator_oversold(**overrides: object) -> IndicatorRecord:
    """Return an IndicatorRecord representing oversold RSI conditions.

    Useful for testing BUY signal generation rules.

    Args:
        **overrides: Any IndicatorRecord field to override.

    Returns:
        A frozen IndicatorRecord instance.
    """
    oversold_defaults: dict[str, object] = {
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "timestamp": _FIXED_TS,
        "rsi": Decimal("28.5000"),
        "bollinger_upper": Decimal("43800.00000000"),
        "bollinger_middle": Decimal("42000.00000000"),
        "bollinger_lower": Decimal("40200.00000000"),
        # Price near the lower band → negative value
        "price_vs_bollinger": Decimal("-0.8500"),
        "harmonic_pattern": None,
        "trend_slope": Decimal("-0.001200"),
        "trend_type": "stable",
        "metadata": {},
    }
    oversold_defaults.update(overrides)
    return IndicatorRecord(**oversold_defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Aliases for import compatibility (tests/factories/__init__.py)
# ---------------------------------------------------------------------------

#: Callable alias for make_ohlcv — use ``make_ohlcv`` directly in tests.
OHLCVRecordFactory: Callable[..., OHLCVRecord] = make_ohlcv

#: Callable alias for make_indicator — use ``make_indicator`` directly in tests.
IndicatorRecordFactory: Callable[..., IndicatorRecord] = make_indicator
