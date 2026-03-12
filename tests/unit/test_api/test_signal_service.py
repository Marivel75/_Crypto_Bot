"""Unit tests for signal_service — active signals, detail, performance, history."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import signal_service
from src.shared.exceptions import NotFoundError
from src.shared.models.orm import SignalOutcomeOrm, TradingSignalOrm


UTC = timezone.utc


class TestGetActive:
    """Get active signals from last 24 hours."""

    @pytest.mark.asyncio
    async def test_get_active_empty(self, db_session: AsyncSession) -> None:
        """Empty signal history returns empty list."""
        signals = await signal_service.get_active(db_session)
        assert signals == []

    @pytest.mark.asyncio
    async def test_get_active_filters_by_24h(self, db_session: AsyncSession) -> None:
        """Only signals from last 24 hours are returned."""
        now = datetime.now(tz=UTC)
        old_time = now - timedelta(hours=25)
        recent_time = now - timedelta(hours=12)

        old_signal = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
            created_at=old_time,
        )
        recent_signal = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
            created_at=recent_time,
        )
        db_session.add(old_signal)
        db_session.add(recent_signal)
        await db_session.flush()

        signals = await signal_service.get_active(db_session)
        assert len(signals) == 1
        assert signals[0].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_get_active_orders_by_created_at_desc(
        self, db_session: AsyncSession
    ) -> None:
        """Active signals are ordered by creation time descending."""
        now = datetime.now(tz=UTC)
        time1 = now - timedelta(hours=5)
        time2 = now - timedelta(hours=10)
        time3 = now - timedelta(hours=15)

        signal1 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
            created_at=time1,
        )
        signal2 = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
            created_at=time2,
        )
        signal3 = TradingSignalOrm(
            symbol="SOLUSDT",
            timeframe_primary="1D",
            direction="HOLD",
            confidence=0.6,
            entry_price=150.0,
            stop_loss=140.0,
            take_profit_list=[160.0],
            leverage_suggested=1,
            indicators_used=["BB"],
            created_at=time3,
        )
        db_session.add(signal1)
        db_session.add(signal2)
        db_session.add(signal3)
        await db_session.flush()

        signals = await signal_service.get_active(db_session)
        assert len(signals) == 3
        assert signals[0].created_at == time1
        assert signals[1].created_at == time2
        assert signals[2].created_at == time3


class TestGetBySymbol:
    """Get signals for a specific symbol."""

    @pytest.mark.asyncio
    async def test_get_by_symbol_empty(self, db_session: AsyncSession) -> None:
        """Non-existent symbol returns empty list."""
        signals, total = await signal_service.get_by_symbol(db_session, "NONEXISTENT")
        assert signals == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_by_symbol_filters_by_symbol(
        self, db_session: AsyncSession
    ) -> None:
        """Only signals for specified symbol are returned."""
        signal1 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
        )
        signal2 = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="1h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
        )
        db_session.add(signal1)
        db_session.add(signal2)
        await db_session.flush()

        signals, total = await signal_service.get_by_symbol(db_session, "BTCUSDT")
        assert len(signals) == 1
        assert total == 1
        assert signals[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_by_symbol_case_insensitive(
        self, db_session: AsyncSession
    ) -> None:
        """Symbol filtering is case-insensitive."""
        signal = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
        )
        db_session.add(signal)
        await db_session.flush()

        signals, total = await signal_service.get_by_symbol(db_session, "btcusdt")
        assert len(signals) == 1
        assert signals[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_by_symbol_with_timeframe_filter(
        self, db_session: AsyncSession
    ) -> None:
        """Timeframe filter narrows results."""
        signal1 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
        )
        signal2 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=50500.0,
            stop_loss=50600.0,
            take_profit_list=[50200.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
        )
        db_session.add(signal1)
        db_session.add(signal2)
        await db_session.flush()

        signals, total = await signal_service.get_by_symbol(
            db_session, "BTCUSDT", timeframe="1h"
        )
        assert len(signals) == 1
        assert total == 1
        assert signals[0].timeframe_primary == "1h"

    @pytest.mark.asyncio
    async def test_get_by_symbol_pagination(self, db_session: AsyncSession) -> None:
        """Pagination works correctly."""
        for i in range(5):
            signal = TradingSignalOrm(
                symbol="BTCUSDT",
                timeframe_primary="1h",
                direction="BUY" if i % 2 == 0 else "SELL",
                confidence=0.7 + (i * 0.01),
                entry_price=50000.0 + (i * 100),
                stop_loss=49000.0,
                take_profit_list=[52000.0],
                leverage_suggested=2,
                indicators_used=["RSI"],
            )
            db_session.add(signal)
        await db_session.flush()

        page1, total = await signal_service.get_by_symbol(
            db_session, "BTCUSDT", limit=2, page=1
        )
        page2, _ = await signal_service.get_by_symbol(
            db_session, "BTCUSDT", limit=2, page=2
        )
        assert len(page1) == 2
        assert len(page2) == 2
        assert total == 5


class TestGetDetail:
    """Get detailed signal with outcome."""

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, db_session: AsyncSession) -> None:
        """Non-existent signal raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await signal_service.get_detail(db_session, "nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_detail_without_outcome(self, db_session: AsyncSession) -> None:
        """Detail returns signal with None outcome when no outcome exists."""
        signal = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
        )
        db_session.add(signal)
        await db_session.flush()

        detail = await signal_service.get_detail(db_session, str(signal.id))
        assert detail["signal"].id == signal.id
        assert detail["outcome"] is None

    @pytest.mark.asyncio
    async def test_get_detail_with_outcome(self, db_session: AsyncSession) -> None:
        """Detail returns signal with outcome when outcome exists."""
        signal = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
        )
        db_session.add(signal)
        await db_session.flush()

        outcome = SignalOutcomeOrm(
            signal_id=signal.id,
            was_correct=True,
            exit_price=52000.0,
            pnl_simulated=100.0,
            exit_timestamp=datetime.now(tz=UTC),
        )
        db_session.add(outcome)
        await db_session.flush()

        detail = await signal_service.get_detail(db_session, str(signal.id))
        assert detail["signal"].id == signal.id
        assert detail["outcome"] is not None
        assert detail["outcome"].was_correct is True
        assert detail["outcome"].pnl_simulated == 100.0


class TestGetPerformance:
    """Signal performance aggregation."""

    @pytest.mark.asyncio
    async def test_get_performance_empty(self, db_session: AsyncSession) -> None:
        """Empty signal history returns zero metrics."""
        perf = await signal_service.get_performance(db_session)
        assert perf["total_signals"] == 0
        assert perf["evaluated_signals"] == 0
        assert perf["correct_signals"] == 0
        assert perf["win_rate"] is None
        assert perf["total_pnl"] is None

    @pytest.mark.asyncio
    async def test_get_performance_with_signals_no_outcomes(
        self, db_session: AsyncSession
    ) -> None:
        """Signals without outcomes count toward total but not evaluated."""
        for i in range(3):
            signal = TradingSignalOrm(
                symbol="BTCUSDT",
                timeframe_primary="1h",
                direction="BUY",
                confidence=0.7,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit_list=[52000.0],
                leverage_suggested=2,
                indicators_used=["RSI"],
            )
            db_session.add(signal)
        await db_session.flush()

        perf = await signal_service.get_performance(db_session)
        assert perf["total_signals"] == 3
        assert perf["evaluated_signals"] == 0
        assert perf["win_rate"] is None

    @pytest.mark.asyncio
    async def test_get_performance_with_mixed_outcomes(
        self, db_session: AsyncSession
    ) -> None:
        """Performance calculates correct win_rate and total_pnl."""
        signal1 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
        )
        signal2 = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
        )
        signal3 = TradingSignalOrm(
            symbol="SOLUSDT",
            timeframe_primary="1D",
            direction="BUY",
            confidence=0.6,
            entry_price=150.0,
            stop_loss=140.0,
            take_profit_list=[160.0],
            leverage_suggested=1,
            indicators_used=["BB"],
        )
        db_session.add(signal1)
        db_session.add(signal2)
        db_session.add(signal3)
        await db_session.flush()

        outcome1 = SignalOutcomeOrm(
            signal_id=signal1.id,
            was_correct=True,
            exit_price=52000.0,
            pnl_simulated=100.0,
            exit_timestamp=datetime.now(tz=UTC),
        )
        outcome2 = SignalOutcomeOrm(
            signal_id=signal2.id,
            was_correct=False,
            exit_price=3050.0,
            pnl_simulated=-50.0,
            exit_timestamp=datetime.now(tz=UTC),
        )
        db_session.add(outcome1)
        db_session.add(outcome2)
        await db_session.flush()

        perf = await signal_service.get_performance(db_session)
        assert perf["total_signals"] == 3
        assert perf["evaluated_signals"] == 2
        assert perf["correct_signals"] == 1
        assert perf["win_rate"] == 50.0
        assert perf["total_pnl"] == 50.0


class TestGetHistory:
    """Signal history with pagination and date filtering."""

    @pytest.mark.asyncio
    async def test_get_history_empty(self, db_session: AsyncSession) -> None:
        """Empty signal history returns empty list."""
        signals, total = await signal_service.get_history(db_session)
        assert signals == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_history_no_filters(self, db_session: AsyncSession) -> None:
        """History without filters returns all signals."""
        for i in range(3):
            signal = TradingSignalOrm(
                symbol="BTCUSDT",
                timeframe_primary="1h",
                direction="BUY",
                confidence=0.7,
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit_list=[52000.0],
                leverage_suggested=2,
                indicators_used=["RSI"],
            )
            db_session.add(signal)
        await db_session.flush()

        signals, total = await signal_service.get_history(db_session)
        assert len(signals) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_history_filter_by_start_date(
        self, db_session: AsyncSession
    ) -> None:
        """Start date filter includes only signals created after start time."""
        now = datetime.now(tz=UTC)
        old_time = now - timedelta(hours=5)
        new_time = now - timedelta(hours=1)

        old_signal = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
            created_at=old_time,
        )
        new_signal = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
            created_at=new_time,
        )
        db_session.add(old_signal)
        db_session.add(new_signal)
        await db_session.flush()

        start_time = now - timedelta(hours=2)
        signals, total = await signal_service.get_history(db_session, start=start_time)
        assert len(signals) == 1
        assert total == 1
        assert signals[0].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_get_history_filter_by_end_date(
        self, db_session: AsyncSession
    ) -> None:
        """End date filter includes only signals created before end time."""
        now = datetime.now(tz=UTC)
        old_time = now - timedelta(hours=5)
        new_time = now - timedelta(hours=1)

        old_signal = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
            created_at=old_time,
        )
        new_signal = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
            created_at=new_time,
        )
        db_session.add(old_signal)
        db_session.add(new_signal)
        await db_session.flush()

        end_time = now - timedelta(hours=2)
        signals, total = await signal_service.get_history(db_session, end=end_time)
        assert len(signals) == 1
        assert total == 1
        assert signals[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_history_filter_by_date_range(
        self, db_session: AsyncSession
    ) -> None:
        """Date range filter includes only signals within range."""
        now = datetime.now(tz=UTC)
        time1 = now - timedelta(hours=10)
        time2 = now - timedelta(hours=5)
        time3 = now - timedelta(hours=1)

        signal1 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
            created_at=time1,
        )
        signal2 = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
            created_at=time2,
        )
        signal3 = TradingSignalOrm(
            symbol="SOLUSDT",
            timeframe_primary="1D",
            direction="BUY",
            confidence=0.6,
            entry_price=150.0,
            stop_loss=140.0,
            take_profit_list=[160.0],
            leverage_suggested=1,
            indicators_used=["BB"],
            created_at=time3,
        )
        db_session.add(signal1)
        db_session.add(signal2)
        db_session.add(signal3)
        await db_session.flush()

        start_time = now - timedelta(hours=7)
        end_time = now - timedelta(hours=2)
        signals, total = await signal_service.get_history(
            db_session, start=start_time, end=end_time
        )
        assert len(signals) == 1
        assert total == 1
        assert signals[0].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_get_history_pagination(self, db_session: AsyncSession) -> None:
        """Pagination works correctly with limit and page."""
        for i in range(5):
            signal = TradingSignalOrm(
                symbol="BTCUSDT",
                timeframe_primary="1h",
                direction="BUY" if i % 2 == 0 else "SELL",
                confidence=0.7 + (i * 0.01),
                entry_price=50000.0 + (i * 100),
                stop_loss=49000.0,
                take_profit_list=[52000.0],
                leverage_suggested=2,
                indicators_used=["RSI"],
            )
            db_session.add(signal)
        await db_session.flush()

        page1, total = await signal_service.get_history(
            db_session, limit=2, page=1
        )
        page2, _ = await signal_service.get_history(db_session, limit=2, page=2)
        page3, _ = await signal_service.get_history(db_session, limit=2, page=3)
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_history_orders_by_created_at_desc(
        self, db_session: AsyncSession
    ) -> None:
        """History is ordered by creation time descending."""
        now = datetime.now(tz=UTC)
        time1 = now - timedelta(hours=5)
        time2 = now - timedelta(hours=10)
        time3 = now - timedelta(hours=15)

        signal1 = TradingSignalOrm(
            symbol="BTCUSDT",
            timeframe_primary="1h",
            direction="BUY",
            confidence=0.7,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_list=[52000.0],
            leverage_suggested=2,
            indicators_used=["RSI"],
            created_at=time1,
        )
        signal2 = TradingSignalOrm(
            symbol="ETHUSDT",
            timeframe_primary="4h",
            direction="SELL",
            confidence=0.8,
            entry_price=3000.0,
            stop_loss=3100.0,
            take_profit_list=[2900.0],
            leverage_suggested=1,
            indicators_used=["MACD"],
            created_at=time2,
        )
        signal3 = TradingSignalOrm(
            symbol="SOLUSDT",
            timeframe_primary="1D",
            direction="BUY",
            confidence=0.6,
            entry_price=150.0,
            stop_loss=140.0,
            take_profit_list=[160.0],
            leverage_suggested=1,
            indicators_used=["BB"],
            created_at=time3,
        )
        db_session.add(signal1)
        db_session.add(signal2)
        db_session.add(signal3)
        await db_session.flush()

        signals, _ = await signal_service.get_history(db_session)
        assert len(signals) == 3
        assert signals[0].created_at == time1
        assert signals[1].created_at == time2
        assert signals[2].created_at == time3
