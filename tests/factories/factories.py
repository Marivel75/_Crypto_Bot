"""Consolidated factory module for all test data.

Re-exports every factory function and alias from the individual factory
sub-modules so callers can use a single import path:

    from tests.factories.factories import make_ohlcv, make_signal, make_user

All timestamps are fixed — never ``datetime.now()`` in test data.
No real database session is needed; factories return in-memory objects.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Crypto factories (OHLCVRecord, IndicatorRecord)
# ---------------------------------------------------------------------------
from tests.factories.crypto_factory import (
    IndicatorRecordFactory,
    OHLCVRecordFactory,
    make_indicator,
    make_indicator_oversold,
    make_ohlcv,
    make_ohlcv_eth,
)

# ---------------------------------------------------------------------------
# Signal factories (TradingSignal)
# ---------------------------------------------------------------------------
from tests.factories.signal_factory import (
    TradingSignalFactory,
    make_hold_signal,
    make_sell_signal,
    make_signal,
)

# ---------------------------------------------------------------------------
# User factories (UserOrm)
# ---------------------------------------------------------------------------
from tests.factories.user_factory import (
    UserOrmFactory,
    make_investor_user,
    make_journalist_user,
    make_user,
)

__all__ = [
    # Crypto
    "make_ohlcv",
    "make_ohlcv_eth",
    "make_indicator",
    "make_indicator_oversold",
    "OHLCVRecordFactory",
    "IndicatorRecordFactory",
    # Signal
    "make_signal",
    "make_sell_signal",
    "make_hold_signal",
    "TradingSignalFactory",
    # User
    "make_user",
    "make_journalist_user",
    "make_investor_user",
    "UserOrmFactory",
]
