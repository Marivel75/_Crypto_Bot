"""Test factories for trading signal Pydantic models.

Provides helper functions returning TradingSignal instances with realistic
defaults. All timestamps are fixed — never datetime.now().

The alias ``TradingSignalFactory`` is provided for import compatibility
with the package ``__init__.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from src.shared.models.signal import TradingSignal

# Fixed reference timestamp aligned with crypto_factory._FIXED_TS
_FIXED_TS = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)


def make_signal(**overrides: object) -> TradingSignal:
    """Return a TradingSignal with a confident BUY on BTCUSDT.

    Defaults reflect a multi-timeframe RSI convergence BUY signal with
    confidence above the 0.6 emission threshold.

    Args:
        **overrides: Any TradingSignal field to override.

    Returns:
        A frozen TradingSignal instance.
    """
    defaults: dict[str, object] = {
        "symbol": "BTCUSDT",
        "signal_type": "BUY",
        "confidence_score": Decimal("0.7800"),
        "timeframe_primary": "4h",
        "timeframes_aligned": {
            "1h": {"rsi": 66},
            "2h": {"rsi": 67},
            "3h": {"rsi": 67},
            "4h": {"rsi": 68},
        },
        "rules_triggered": ["rsi_convergence_multi_tf", "bollinger_squeeze"],
        "leverage_suggested": 5,
        "margin_safety": Decimal("2.0000"),
        "fees_estimated": Decimal("0.000750"),
        "model_version": "rules_v1",
        "created_at": _FIXED_TS,
    }
    defaults.update(overrides)
    return TradingSignal(**defaults)  # type: ignore[arg-type]


def make_sell_signal(**overrides: object) -> TradingSignal:
    """Return a TradingSignal representing a SELL with overbought RSI.

    Args:
        **overrides: Any TradingSignal field to override.

    Returns:
        A frozen TradingSignal instance.
    """
    sell_defaults: dict[str, object] = {
        "symbol": "ETHUSDT",
        "signal_type": "SELL",
        "confidence_score": Decimal("0.6500"),
        "timeframe_primary": "4h",
        "timeframes_aligned": {
            "1h": {"rsi": 74},
            "2h": {"rsi": 73},
            "3h": {"rsi": 72},
            "4h": {"rsi": 71},
        },
        "rules_triggered": ["rsi_overbought_multi_tf"],
        "leverage_suggested": 5,
        "margin_safety": Decimal("2.0000"),
        "fees_estimated": Decimal("0.000750"),
        "model_version": "rules_v1",
        "created_at": _FIXED_TS,
    }
    sell_defaults.update(overrides)
    return TradingSignal(**sell_defaults)  # type: ignore[arg-type]


def make_hold_signal(**overrides: object) -> TradingSignal:
    """Return a TradingSignal with HOLD direction (no clear edge).

    Confidence is at the minimum emission threshold (0.60).

    Args:
        **overrides: Any TradingSignal field to override.

    Returns:
        A frozen TradingSignal instance.
    """
    hold_defaults: dict[str, object] = {
        "symbol": "BTCUSDT",
        "signal_type": "HOLD",
        "confidence_score": Decimal("0.6000"),
        "timeframe_primary": "1h",
        "timeframes_aligned": {
            "1h": {"rsi": 52},
            "4h": {"rsi": 49},
        },
        "rules_triggered": [],
        "leverage_suggested": None,
        "margin_safety": None,
        "fees_estimated": None,
        "model_version": "rules_v1",
        "created_at": _FIXED_TS,
    }
    hold_defaults.update(overrides)
    return TradingSignal(**hold_defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Alias for import compatibility (tests/factories/__init__.py)
# ---------------------------------------------------------------------------

#: Callable alias for make_signal — use ``make_signal`` directly in tests.
TradingSignalFactory: Callable[..., TradingSignal] = make_signal
