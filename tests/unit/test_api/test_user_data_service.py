"""Unit tests for user_data_service — portfolio and watchlist operations."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import user_data_service
from src.shared.exceptions import AuthorizationError, ConflictError, NotFoundError
from src.shared.models.orm import OHLCVOrm, PortfolioEntryOrm, WatchlistEntryOrm, UserOrm


UTC = timezone.utc


class TestPortfolioCRUD:
    """Portfolio CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_portfolio_empty(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Empty portfolio returns empty list."""
        entries = await user_data_service.get_portfolio(db_session, str(test_user.id))
        assert entries == []

    @pytest.mark.asyncio
    async def test_add_portfolio_entry_happy_path(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Add a portfolio entry and verify it's stored."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "BTC", 0.5, 45000.0, "My Bitcoin"
        )
        assert entry.symbol == "BTC"
        assert entry.quantity == 0.5
        assert entry.entry_price == 45000.0
        assert entry.notes == "My Bitcoin"

    @pytest.mark.asyncio
    async def test_add_portfolio_entry_symbol_uppercase(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Symbol is automatically uppercased."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "btc", 1.0, 50000.0
        )
        assert entry.symbol == "BTC"

    @pytest.mark.asyncio
    async def test_get_portfolio_after_add(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Retrieving portfolio after adding shows the entry."""
        await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "ETH", 2.0, 2000.0
        )
        entries = await user_data_service.get_portfolio(db_session, str(test_user.id))
        assert len(entries) == 1
        assert entries[0].symbol == "ETH"

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_quantity(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Update entry quantity."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "SOL", 10.0, 100.0
        )
        updated = await user_data_service.update_portfolio_entry(
            db_session, str(test_user.id), str(entry.id), quantity=15.0
        )
        assert updated.quantity == 15.0
        assert updated.entry_price == 100.0

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_price(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Update entry price."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "ADA", 100.0, 0.50
        )
        updated = await user_data_service.update_portfolio_entry(
            db_session, str(test_user.id), str(entry.id), entry_price=0.60
        )
        assert updated.entry_price == 0.60
        assert updated.quantity == 100.0

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_not_found(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Update nonexistent entry raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await user_data_service.update_portfolio_entry(
                db_session, str(test_user.id), "nonexistent-id", quantity=1.0
            )

    @pytest.mark.asyncio
    async def test_update_portfolio_entry_wrong_owner(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Update entry owned by another user raises AuthorizationError."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "DOGE", 1000.0, 0.10
        )
        with pytest.raises(AuthorizationError):
            await user_data_service.update_portfolio_entry(
                db_session, "other-user-id", str(entry.id), quantity=2000.0
            )

    @pytest.mark.asyncio
    async def test_delete_portfolio_entry(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Delete removes the entry."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "XRP", 500.0, 1.00
        )
        await user_data_service.delete_portfolio_entry(db_session, str(test_user.id), str(entry.id))
        entries = await user_data_service.get_portfolio(db_session, str(test_user.id))
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_delete_portfolio_entry_not_found(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Delete nonexistent entry raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await user_data_service.delete_portfolio_entry(
                db_session, str(test_user.id), "nonexistent-id"
            )

    @pytest.mark.asyncio
    async def test_delete_portfolio_entry_wrong_owner(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Delete entry owned by another user raises AuthorizationError."""
        entry = await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "USDT", 1000.0, 1.00
        )
        with pytest.raises(AuthorizationError):
            await user_data_service.delete_portfolio_entry(
                db_session, "other-user-id", str(entry.id)
            )


class TestWatchlistCRUD:
    """Watchlist CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_watchlist_empty(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Empty watchlist returns empty list."""
        entries = await user_data_service.get_watchlist(db_session, str(test_user.id))
        assert entries == []

    @pytest.mark.asyncio
    async def test_add_watchlist_symbol(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Add symbol to watchlist."""
        entry = await user_data_service.add_watchlist_symbol(
            db_session, str(test_user.id), "BTC"
        )
        assert entry.symbol == "BTC"

    @pytest.mark.asyncio
    async def test_add_watchlist_symbol_uppercase(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Symbol is automatically uppercased."""
        entry = await user_data_service.add_watchlist_symbol(
            db_session, str(test_user.id), "eth"
        )
        assert entry.symbol == "ETH"

    @pytest.mark.asyncio
    async def test_add_watchlist_duplicate_raises(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Adding duplicate symbol raises ConflictError."""
        await user_data_service.add_watchlist_symbol(
            db_session, str(test_user.id), "SOL"
        )
        with pytest.raises(ConflictError):
            await user_data_service.add_watchlist_symbol(
                db_session, str(test_user.id), "SOL"
            )

    @pytest.mark.asyncio
    async def test_remove_watchlist_symbol(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Remove symbol from watchlist."""
        await user_data_service.add_watchlist_symbol(
            db_session, str(test_user.id), "ADA"
        )
        await user_data_service.remove_watchlist_symbol(
            db_session, str(test_user.id), "ADA"
        )
        entries = await user_data_service.get_watchlist(db_session, str(test_user.id))
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_remove_watchlist_not_found(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Remove nonexistent symbol raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await user_data_service.remove_watchlist_symbol(
                db_session, str(test_user.id), "NONEXISTENT"
            )


class TestPortfolioSummary:
    """Portfolio summary aggregation."""

    @pytest.mark.asyncio
    async def test_portfolio_summary_empty(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Empty portfolio summary returns zero values."""
        summary = await user_data_service.get_portfolio_summary(db_session, str(test_user.id))
        assert summary["total_entries"] == 0
        assert summary["total_value"] is None
        assert summary["total_cost"] is None
        assert summary["allocation"] == {}

    @pytest.mark.asyncio
    async def test_portfolio_summary_single_entry(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Single entry portfolio shows 100% allocation."""
        await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "BTC", 1.0, 50000.0
        )
        summary = await user_data_service.get_portfolio_summary(db_session, str(test_user.id))
        assert summary["total_entries"] == 1
        assert summary["total_value"] == 50000.0
        assert summary["allocation"]["BTC"] == 100.0

    @pytest.mark.asyncio
    async def test_portfolio_summary_multiple_entries(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Multiple entries show correct allocation percentages."""
        await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "BTC", 1.0, 50000.0  # $50k
        )
        await user_data_service.add_portfolio_entry(
            db_session, str(test_user.id), "ETH", 10.0, 5000.0  # $50k
        )
        summary = await user_data_service.get_portfolio_summary(db_session, str(test_user.id))
        assert summary["total_entries"] == 2
        assert summary["total_value"] == 100000.0
        assert summary["allocation"]["BTC"] == 50.0
        assert summary["allocation"]["ETH"] == 50.0


class TestWatchlistPrices:
    """Watchlist price fetching."""

    @pytest.mark.asyncio
    async def test_watchlist_prices_empty(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Empty watchlist returns empty price list."""
        prices = await user_data_service.get_watchlist_prices(db_session, str(test_user.id))
        assert prices == []

    @pytest.mark.asyncio
    async def test_watchlist_prices_with_data(
        self, db_session: AsyncSession, test_user: UserOrm
    ) -> None:
        """Watchlist prices retrieves latest OHLCV for each symbol."""
        await user_data_service.add_watchlist_symbol(db_session, str(test_user.id), "BTC")

        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        ohlcv = OHLCVOrm(
            symbol="BTC",
            timeframe="1h",
            timestamp=now,
            price_open=50000.0,
            price_high=51000.0,
            price_low=49000.0,
            price_close=50500.0,
            volume_24h=100.0,
            source="binance",
        )
        db_session.add(ohlcv)
        await db_session.flush()

        prices = await user_data_service.get_watchlist_prices(db_session, str(test_user.id))
        assert len(prices) == 1
        assert prices[0]["symbol"] == "BTC"
        assert prices[0]["current_price"] == 50500.0
        assert prices[0]["timestamp"] == now

    @pytest.mark.asyncio
    async def test_watchlist_prices_latest_only(
        self, db_session: AsyncSession, test_user: UserOrm
    ) -> None:
        """Watchlist prices returns only the latest OHLCV record."""
        await user_data_service.add_watchlist_symbol(db_session, str(test_user.id), "ETH")

        old_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        new_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        old_ohlcv = OHLCVOrm(
            symbol="ETH",
            timeframe="1h",
            timestamp=old_time,
            price_open=2000.0,
            price_high=2100.0,
            price_low=1900.0,
            price_close=2050.0,
            volume_24h=50.0,
            source="binance",
        )
        new_ohlcv = OHLCVOrm(
            symbol="ETH",
            timeframe="1h",
            timestamp=new_time,
            price_open=2050.0,
            price_high=2150.0,
            price_low=2000.0,
            price_close=2100.0,
            volume_24h=60.0,
            source="binance",
        )
        db_session.add(old_ohlcv)
        db_session.add(new_ohlcv)
        await db_session.flush()

        prices = await user_data_service.get_watchlist_prices(db_session, str(test_user.id))
        assert len(prices) == 1
        assert prices[0]["current_price"] == 2100.0
        assert prices[0]["timestamp"] == new_time
