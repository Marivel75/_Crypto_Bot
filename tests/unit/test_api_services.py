"""Unit tests for API service layer logic with mocked DB sessions.

Tests cover:
- crypto_service: get_prices, get_indicators, get_latest, get_market_overview
- signal_service: get_active, get_by_symbol, get_detail, get_performance
- user_data_service: portfolio CRUD and watchlist CRUD (via AsyncMock)

Crypto/signal tests use the in-memory SQLite session from conftest.py.
Portfolio/watchlist tests use AsyncMock because user_data_service imports
PortfolioEntryOrm/WatchlistEntryOrm at module load time (before conftest can
monkey-patch them), so the real UUID-typed ORM would be used otherwise.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

UTC = timezone.utc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import crypto_service, signal_service
from src.api.services.user_data_service import (
    ConflictError,
    add_portfolio_entry,
    add_watchlist_symbol,
    delete_portfolio_entry,
    get_portfolio,
    get_watchlist,
    remove_watchlist_symbol,
    update_portfolio_entry,
)
from src.shared.exceptions import AuthorizationError, NotFoundError

logger = logging.getLogger(__name__)

# Fixed timestamps — never datetime.now() in tests
_TS = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# Helpers — ORM row builders (using test-compatible ORM from conftest)
# ---------------------------------------------------------------------------

# We import the test-compatible ORM classes that conftest.py defines.
# These are the SQLite-compatible versions used for in-memory DB tests.
from tests.conftest import (  # noqa: E402
    CryptoPriceOrm,
    IndicatorOrm,
    SignalOutcomeOrm,
    TradingSignalOrm,
)


def _make_price_row(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    price_close: float = 50000.0,
    ts: datetime = _TS,
) -> CryptoPriceOrm:
    """Return an unsaved CryptoPriceOrm row."""
    return CryptoPriceOrm(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        price_open=price_close - 200.0,
        price_high=price_close + 300.0,
        price_low=price_close - 400.0,
        price_close=price_close,
        volume_24h=1_000_000.0,
        market_cap=None,
        source="binance",
    )


def _make_indicator_row(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    ts: datetime = _TS,
    rsi: float = 65.0,
) -> IndicatorOrm:
    """Return an unsaved IndicatorOrm row."""
    return IndicatorOrm(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        rsi=rsi,
        bollinger_upper=52000.0,
        bollinger_middle=50000.0,
        bollinger_lower=48000.0,
        price_vs_bollinger=0.2,
    )


def _make_signal_row(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    signal_type: str = "BUY",
    confidence: float = 0.75,
    ts: datetime = _TS,
) -> TradingSignalOrm:
    """Return an unsaved TradingSignalOrm row."""
    return TradingSignalOrm(
        symbol=symbol,
        signal_type=signal_type,
        confidence_score=confidence,
        timeframe_primary=timeframe,
        timeframes_aligned={},
        rules_triggered=["rsi_oversold_multi_tf"],
        leverage_suggested=5,
        margin_safety=2.0,
        fees_estimated=0.001,
        model_version="rules_v1",
        created_at=ts,
    )


# ---------------------------------------------------------------------------
# crypto_service.get_prices
# ---------------------------------------------------------------------------


class TestGetPrices:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_data(self, db_session: AsyncSession) -> None:
        rows, total = await crypto_service.get_prices(db_session, "BTCUSDT", "1h")
        assert rows == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_returns_inserted_rows(self, db_session: AsyncSession) -> None:
        row = _make_price_row()
        db_session.add(row)
        await db_session.commit()

        rows, total = await crypto_service.get_prices(db_session, "BTCUSDT", "1h")
        assert total == 1
        assert len(rows) == 1
        assert rows[0].price_close == 50000.0

    @pytest.mark.asyncio
    async def test_filters_by_symbol(self, db_session: AsyncSession) -> None:
        db_session.add(_make_price_row(symbol="BTCUSDT"))
        db_session.add(_make_price_row(symbol="ETHUSDT"))
        await db_session.commit()

        rows, total = await crypto_service.get_prices(db_session, "BTCUSDT", "1h")
        assert total == 1
        assert rows[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_filters_by_timeframe(self, db_session: AsyncSession) -> None:
        db_session.add(_make_price_row(timeframe="1h"))
        db_session.add(_make_price_row(timeframe="4h", ts=datetime(2025, 1, 15, 16, 0, tzinfo=UTC)))
        await db_session.commit()

        rows, total = await crypto_service.get_prices(db_session, "BTCUSDT", "4h")
        assert total == 1
        assert rows[0].timeframe == "4h"

    @pytest.mark.asyncio
    async def test_symbol_lookup_is_case_insensitive(self, db_session: AsyncSession) -> None:
        db_session.add(_make_price_row(symbol="BTCUSDT"))
        await db_session.commit()

        rows, total = await crypto_service.get_prices(db_session, "btcusdt", "1h")
        assert total == 1

    @pytest.mark.asyncio
    async def test_pagination_limit(self, db_session: AsyncSession) -> None:
        for i in range(5):
            db_session.add(
                _make_price_row(
                    ts=datetime(2025, 1, 15, i, 0, tzinfo=UTC),
                )
            )
        await db_session.commit()

        rows, total = await crypto_service.get_prices(db_session, "BTCUSDT", "1h", limit=3)
        assert total == 5
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_start_filter_excludes_earlier_rows(self, db_session: AsyncSession) -> None:
        early_ts = datetime(2025, 1, 14, 0, 0, tzinfo=UTC)
        late_ts = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
        db_session.add(_make_price_row(ts=early_ts))
        db_session.add(_make_price_row(ts=late_ts))
        await db_session.commit()

        rows, total = await crypto_service.get_prices(
            db_session, "BTCUSDT", "1h", start=datetime(2025, 1, 15, tzinfo=UTC)
        )
        assert total == 1
        # SQLite strips timezone info from DateTime columns — compare naive
        assert rows[0].timestamp == late_ts.replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_end_filter_excludes_later_rows(self, db_session: AsyncSession) -> None:
        early_ts = datetime(2025, 1, 14, 0, 0, tzinfo=UTC)
        late_ts = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
        db_session.add(_make_price_row(ts=early_ts))
        db_session.add(_make_price_row(ts=late_ts))
        await db_session.commit()

        rows, total = await crypto_service.get_prices(
            db_session, "BTCUSDT", "1h", end=datetime(2025, 1, 15, tzinfo=UTC)
        )
        assert total == 1
        # SQLite strips timezone info from DateTime columns — compare naive
        assert rows[0].timestamp == early_ts.replace(tzinfo=None)


# ---------------------------------------------------------------------------
# crypto_service.get_indicators
# ---------------------------------------------------------------------------


class TestGetIndicators:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_data(self, db_session: AsyncSession) -> None:
        rows, total = await crypto_service.get_indicators(db_session, "BTCUSDT", "1h")
        assert rows == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_returns_inserted_rows(self, db_session: AsyncSession) -> None:
        row = _make_indicator_row()
        db_session.add(row)
        await db_session.commit()

        rows, total = await crypto_service.get_indicators(db_session, "BTCUSDT", "1h")
        assert total == 1
        assert rows[0].rsi == 65.0

    @pytest.mark.asyncio
    async def test_filters_by_symbol(self, db_session: AsyncSession) -> None:
        db_session.add(_make_indicator_row(symbol="BTCUSDT"))
        db_session.add(_make_indicator_row(symbol="ETHUSDT"))
        await db_session.commit()

        rows, total = await crypto_service.get_indicators(db_session, "ETHUSDT", "1h")
        assert total == 1
        assert rows[0].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_pagination_limit(self, db_session: AsyncSession) -> None:
        for i in range(4):
            db_session.add(_make_indicator_row(ts=datetime(2025, 1, 15, i, 0, tzinfo=UTC)))
        await db_session.commit()

        rows, total = await crypto_service.get_indicators(db_session, "BTCUSDT", "1h", limit=2)
        assert total == 4
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# crypto_service.get_latest
# ---------------------------------------------------------------------------


class TestGetLatest:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_data(self, db_session: AsyncSession) -> None:
        result = await crypto_service.get_latest(db_session, "BTCUSDT")
        assert result["symbol"] == "BTCUSDT"
        assert result["ohlcv"] is None
        assert result["indicators"] is None

    @pytest.mark.asyncio
    async def test_returns_most_recent_ohlcv(self, db_session: AsyncSession) -> None:
        old_ts = datetime(2025, 1, 14, 0, 0, tzinfo=UTC)
        new_ts = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
        db_session.add(_make_price_row(ts=old_ts))
        db_session.add(_make_price_row(ts=new_ts, price_close=51000.0))
        await db_session.commit()

        result = await crypto_service.get_latest(db_session, "BTCUSDT")
        assert result["ohlcv"] is not None
        assert result["ohlcv"].price_close == 51000.0

    @pytest.mark.asyncio
    async def test_returns_most_recent_indicator(self, db_session: AsyncSession) -> None:
        old_ts = datetime(2025, 1, 14, 0, 0, tzinfo=UTC)
        new_ts = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
        db_session.add(_make_indicator_row(ts=old_ts, rsi=55.0))
        db_session.add(_make_indicator_row(ts=new_ts, rsi=72.0))
        await db_session.commit()

        result = await crypto_service.get_latest(db_session, "BTCUSDT")
        assert result["indicators"] is not None
        assert result["indicators"].rsi == 72.0


# ---------------------------------------------------------------------------
# signal_service.get_active
# ---------------------------------------------------------------------------


class TestGetActiveSignals:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_signals(self, db_session: AsyncSession) -> None:
        result = await signal_service.get_active(db_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_recent_signals(self, db_session: AsyncSession) -> None:
        # Signal created 1 hour ago — should be active (within 24h window)
        from datetime import timedelta

        recent_ts = datetime.now(tz=UTC) - timedelta(hours=1)
        signal = _make_signal_row(ts=recent_ts)
        db_session.add(signal)
        await db_session.commit()

        result = await signal_service.get_active(db_session)
        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_excludes_old_signals(self, db_session: AsyncSession) -> None:
        from datetime import timedelta

        old_ts = datetime.now(tz=UTC) - timedelta(hours=25)
        signal = _make_signal_row(ts=old_ts)
        db_session.add(signal)
        await db_session.commit()

        result = await signal_service.get_active(db_session)
        assert result == []


# ---------------------------------------------------------------------------
# signal_service.get_by_symbol
# ---------------------------------------------------------------------------


class TestGetBySymbol:
    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_symbol(self, db_session: AsyncSession) -> None:
        rows, total = await signal_service.get_by_symbol(db_session, "UNKNOWN")
        assert rows == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_returns_signals_for_symbol(self, db_session: AsyncSession) -> None:
        db_session.add(_make_signal_row(symbol="BTCUSDT"))
        db_session.add(_make_signal_row(symbol="ETHUSDT", ts=datetime(2025, 1, 15, 13, 0, tzinfo=UTC)))
        await db_session.commit()

        rows, total = await signal_service.get_by_symbol(db_session, "BTCUSDT")
        assert total == 1
        assert rows[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_symbol_lookup_is_case_insensitive(self, db_session: AsyncSession) -> None:
        db_session.add(_make_signal_row(symbol="BTCUSDT"))
        await db_session.commit()

        rows, total = await signal_service.get_by_symbol(db_session, "btcusdt")
        assert total == 1

    @pytest.mark.asyncio
    async def test_filters_by_timeframe(self, db_session: AsyncSession) -> None:
        db_session.add(_make_signal_row(timeframe="4h"))
        db_session.add(_make_signal_row(timeframe="1h", ts=datetime(2025, 1, 15, 13, 0, tzinfo=UTC)))
        await db_session.commit()

        rows, total = await signal_service.get_by_symbol(db_session, "BTCUSDT", timeframe="4h")
        assert total == 1
        assert rows[0].timeframe_primary == "4h"

    @pytest.mark.asyncio
    async def test_pagination_limit(self, db_session: AsyncSession) -> None:
        for i in range(5):
            db_session.add(_make_signal_row(ts=datetime(2025, 1, 15, i, 0, tzinfo=UTC)))
        await db_session.commit()

        rows, total = await signal_service.get_by_symbol(db_session, "BTCUSDT", limit=3)
        assert total == 5
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# signal_service.get_detail
# ---------------------------------------------------------------------------


class TestGetDetail:
    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_id(self, db_session: AsyncSession) -> None:
        with pytest.raises(NotFoundError, match="Signal"):
            await signal_service.get_detail(db_session, "nonexistent-id")

    @pytest.mark.asyncio
    async def test_returns_signal_and_no_outcome(self, db_session: AsyncSession) -> None:
        signal = _make_signal_row()
        db_session.add(signal)
        await db_session.commit()
        await db_session.refresh(signal)

        result = await signal_service.get_detail(db_session, signal.id)
        assert result["signal"].id == signal.id
        assert result["outcome"] is None

    @pytest.mark.asyncio
    async def test_returns_signal_with_outcome(self, db_session: AsyncSession) -> None:
        signal = _make_signal_row()
        db_session.add(signal)
        await db_session.flush()
        await db_session.refresh(signal)

        outcome = SignalOutcomeOrm(
            signal_id=signal.id,
            price_at_signal=50000.0,
            price_after_1h=50500.0,
            was_correct=True,
            evaluated_at=_TS,
        )
        db_session.add(outcome)
        await db_session.commit()

        result = await signal_service.get_detail(db_session, signal.id)
        assert result["outcome"] is not None
        assert result["outcome"].was_correct is True


# ---------------------------------------------------------------------------
# signal_service.get_performance
# ---------------------------------------------------------------------------


class TestGetPerformance:
    @pytest.mark.asyncio
    async def test_returns_zeros_when_empty(self, db_session: AsyncSession) -> None:
        result = await signal_service.get_performance(db_session)
        assert result["total_signals"] == 0
        assert result["evaluated_signals"] == 0
        assert result["correct_signals"] == 0
        assert result["win_rate"] is None

    @pytest.mark.asyncio
    async def test_counts_signals_correctly(self, db_session: AsyncSession) -> None:
        for i in range(3):
            db_session.add(_make_signal_row(ts=datetime(2025, 1, 15, i, 0, tzinfo=UTC)))
        await db_session.commit()

        result = await signal_service.get_performance(db_session)
        assert result["total_signals"] == 3

    @pytest.mark.asyncio
    async def test_win_rate_computed_correctly(self, db_session: AsyncSession) -> None:
        signal1 = _make_signal_row(ts=datetime(2025, 1, 15, 0, 0, tzinfo=UTC))
        signal2 = _make_signal_row(ts=datetime(2025, 1, 15, 1, 0, tzinfo=UTC))
        db_session.add(signal1)
        db_session.add(signal2)
        await db_session.flush()
        await db_session.refresh(signal1)
        await db_session.refresh(signal2)

        # 1 correct out of 2 evaluated = 50% win rate
        outcome1 = SignalOutcomeOrm(
            signal_id=signal1.id,
            price_at_signal=50000.0,
            was_correct=True,
            evaluated_at=_TS,
        )
        outcome2 = SignalOutcomeOrm(
            signal_id=signal2.id,
            price_at_signal=50000.0,
            was_correct=False,
            evaluated_at=_TS,
        )
        db_session.add(outcome1)
        db_session.add(outcome2)
        await db_session.commit()

        result = await signal_service.get_performance(db_session)
        assert result["evaluated_signals"] == 2
        assert result["correct_signals"] == 1
        assert result["win_rate"] == 50.0


# ---------------------------------------------------------------------------
# user_data_service — portfolio CRUD (mocked session)
#
# user_data_service imports PortfolioEntryOrm at module load time, before
# conftest can monkey-patch it. We therefore mock db.execute / db.flush /
# db.refresh / db.delete at the session level to keep tests hermetic.
# ---------------------------------------------------------------------------


def _make_portfolio_mock(
    entry_id: str = "entry-id-1",
    user_id: str = "test-user-id",
    symbol: str = "BTC",
    quantity: float = 1.0,
    entry_price: float = 50000.0,
    notes: str | None = None,
) -> MagicMock:
    """Return a MagicMock shaped like a PortfolioEntryOrm row."""
    entry = MagicMock()
    entry.id = entry_id
    entry.user_id = user_id
    entry.symbol = symbol
    entry.quantity = quantity
    entry.entry_price = entry_price
    entry.notes = notes
    return entry


def _make_watchlist_mock(
    entry_id: str = "wl-id-1",
    user_id: str = "test-user-id",
    symbol: str = "BTC",
) -> MagicMock:
    """Return a MagicMock shaped like a WatchlistEntryOrm row."""
    entry = MagicMock()
    entry.id = entry_id
    entry.user_id = user_id
    entry.symbol = symbol
    return entry


class TestPortfolioService:
    """Tests for user_data_service portfolio functions using a mocked session."""

    @pytest.mark.asyncio
    async def test_get_portfolio_returns_empty_list(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        entries = await get_portfolio(db, "user-1")
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_portfolio_returns_rows(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entries = [
            _make_portfolio_mock(),
            _make_portfolio_mock(entry_id="e2", symbol="ETH"),
        ]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = fake_entries
        db.execute = AsyncMock(return_value=result_mock)

        entries = await get_portfolio(db, "user-1")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_add_portfolio_entry_symbols_uppercased(self) -> None:
        """add_portfolio_entry uppercases the symbol before persisting."""
        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()
        fake_entry = _make_portfolio_mock(symbol="BTC")
        db.refresh = AsyncMock()

        with patch("src.api.services.user_data_service.PortfolioEntryOrm", return_value=fake_entry):
            entry = await add_portfolio_entry(db, "user-1", "btc", 0.5, 40000.0)

        assert entry.symbol == "BTC"

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_not_found_raises(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(NotFoundError):
            await update_portfolio_entry(db, "user-1", "no-such-id", quantity=2.0)

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_wrong_owner_raises(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entry = _make_portfolio_mock(user_id="owner-id")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_entry
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthorizationError):
            await update_portfolio_entry(db, "attacker-id", "entry-id-1", quantity=2.0)

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_updates_fields(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entry = _make_portfolio_mock(quantity=1.0, entry_price=50000.0)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_entry
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        updated = await update_portfolio_entry(
            db, "test-user-id", "entry-id-1", quantity=3.0, entry_price=45000.0, notes="updated"
        )
        assert updated.quantity == 3.0
        assert updated.entry_price == 45000.0
        assert updated.notes == "updated"

    @pytest.mark.asyncio
    async def test_delete_portfolio_entry_not_found_raises(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(NotFoundError):
            await delete_portfolio_entry(db, "user-1", "no-such-id")

    @pytest.mark.asyncio
    async def test_delete_portfolio_entry_wrong_owner_raises(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entry = _make_portfolio_mock(user_id="owner-id")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_entry
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthorizationError):
            await delete_portfolio_entry(db, "attacker-id", "entry-id-1")

    @pytest.mark.asyncio
    async def test_delete_portfolio_entry_calls_db_delete(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entry = _make_portfolio_mock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_entry
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        await delete_portfolio_entry(db, "test-user-id", "entry-id-1")
        db.delete.assert_called_once_with(fake_entry)


# ---------------------------------------------------------------------------
# user_data_service — watchlist CRUD (mocked session)
# ---------------------------------------------------------------------------


class TestWatchlistService:
    """Tests for user_data_service watchlist functions using a mocked session."""

    @pytest.mark.asyncio
    async def test_get_watchlist_returns_empty_list(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        entries = await get_watchlist(db, "user-1")
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_watchlist_returns_rows(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entries = [
            _make_watchlist_mock(),
            _make_watchlist_mock(entry_id="w2", symbol="ETH"),
        ]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = fake_entries
        db.execute = AsyncMock(return_value=result_mock)

        entries = await get_watchlist(db, "user-1")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_add_watchlist_symbol_uppercased(self) -> None:
        """add_watchlist_symbol uppercases the symbol before persisting."""
        db = AsyncMock(spec=AsyncSession)
        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = None  # no duplicate
        db.execute = AsyncMock(return_value=check_result)
        db.flush = AsyncMock()
        # Capture the entry passed to db.add and make db.refresh populate symbol
        added_entries: list[object] = []

        def _capture_add(entry: object) -> None:
            added_entries.append(entry)

        db.add.side_effect = _capture_add
        db.refresh = AsyncMock()

        await add_watchlist_symbol(db, "user-1", "btc")

        assert len(added_entries) == 1
        added = added_entries[0]
        assert added.symbol == "BTC"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_add_duplicate_watchlist_symbol_raises_conflict(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        check_result = MagicMock()
        check_result.scalar_one_or_none.return_value = _make_watchlist_mock()
        db.execute = AsyncMock(return_value=check_result)

        with pytest.raises(ConflictError):
            await add_watchlist_symbol(db, "user-1", "BTC")

    @pytest.mark.asyncio
    async def test_remove_watchlist_symbol_calls_db_delete(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        fake_entry = _make_watchlist_mock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_entry
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        await remove_watchlist_symbol(db, "user-1", "BTC")
        db.delete.assert_called_once_with(fake_entry)

    @pytest.mark.asyncio
    async def test_remove_nonexistent_watchlist_symbol_raises(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(NotFoundError):
            await remove_watchlist_symbol(db, "user-1", "UNKNOWN")
