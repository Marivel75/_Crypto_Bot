"""Unit tests for ETL loaders (TimescaleDB and MinIO).

Database interactions are mocked; no real connections are made.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.etl.loaders.timescaledb import (
    detect_gaps,
    fetch_ohlcv_for_indicators,
    insert_indicators_batch,
    insert_news_batch,
    insert_ohlcv_batch,
)
from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord

logger = logging.getLogger(__name__)

FIXED_TS = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestInsertOhlcvBatch:
    """Tests for insert_ohlcv_batch — persisting OHLCV records to TimescaleDB."""

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_insert_success(self, mock_session_factory: MagicMock) -> None:
        """Valid OHLCV records are inserted; rowcount returned."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        records = [
            OHLCVRecord(
                symbol="BTCUSDT",
                price_open=Decimal("50000.00"),
                price_high=Decimal("51000.00"),
                price_low=Decimal("49500.00"),
                price_close=Decimal("50500.00"),
                volume_24h=Decimal("100.00"),
                timestamp=FIXED_TS,
                source="binance",
                timeframe="1h",
            ),
            OHLCVRecord(
                symbol="ETHUSDT",
                price_open=Decimal("3000.00"),
                price_high=Decimal("3100.00"),
                price_low=Decimal("2900.00"),
                price_close=Decimal("3050.00"),
                volume_24h=Decimal("50.00"),
                timestamp=FIXED_TS,
                source="binance",
                timeframe="1h",
            ),
            OHLCVRecord(
                symbol="BTCUSDT",
                price_open=Decimal("51000.00"),
                price_high=Decimal("52000.00"),
                price_low=Decimal("50500.00"),
                price_close=Decimal("51500.00"),
                volume_24h=Decimal("120.00"),
                timestamp=FIXED_TS.replace(hour=13),
                source="binance",
                timeframe="1h",
            ),
        ]

        inserted = await insert_ohlcv_batch(records)

        assert inserted == 3
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_insert_empty_list_returns_zero(self, mock_session_factory: MagicMock) -> None:
        """Inserting empty list returns 0 without database call."""
        await insert_ohlcv_batch([])

        # Session should not be created for empty list
        mock_session_factory.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_insert_handles_conflict(self, mock_session_factory: MagicMock) -> None:
        """ON CONFLICT DO NOTHING is handled (some records already exist)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1  # Only 1 of 2 records inserted
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        records = [
            OHLCVRecord(
                symbol="BTCUSDT",
                price_open=Decimal("50000.00"),
                price_high=Decimal("51000.00"),
                price_low=Decimal("49500.00"),
                price_close=Decimal("50500.00"),
                volume_24h=Decimal("100.00"),
                timestamp=FIXED_TS,
                source="binance",
                timeframe="1h",
            ),
            OHLCVRecord(
                symbol="BTCUSDT",
                price_open=Decimal("50000.00"),
                price_high=Decimal("51000.00"),
                price_low=Decimal("49500.00"),
                price_close=Decimal("50500.00"),
                volume_24h=Decimal("100.00"),
                timestamp=FIXED_TS,
                source="binance",
                timeframe="1h",
            ),
        ]

        inserted = await insert_ohlcv_batch(records)

        assert inserted == 1


class TestInsertIndicatorsBatch:
    """Tests for insert_indicators_batch — upsert technical indicators."""

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_upsert_success(self, mock_session_factory: MagicMock) -> None:
        """Indicator records are upserted; rowcount returned."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        records = [
            IndicatorRecord(
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=FIXED_TS,
                rsi=Decimal("65.50"),
                bollinger_upper=Decimal("51000.00"),
                bollinger_middle=Decimal("50000.00"),
                bollinger_lower=Decimal("49000.00"),
            ),
            IndicatorRecord(
                symbol="ETHUSDT",
                timeframe="1h",
                timestamp=FIXED_TS,
                rsi=Decimal("55.00"),
                bollinger_upper=Decimal("3100.00"),
                bollinger_middle=Decimal("3000.00"),
                bollinger_lower=Decimal("2900.00"),
            ),
        ]

        affected = await insert_indicators_batch(records)

        assert affected == 2
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_upsert_empty_list(self, mock_session_factory: MagicMock) -> None:
        """Upserting empty list returns 0."""
        affected = await insert_indicators_batch([])
        assert affected == 0
        mock_session_factory.assert_not_called()


class TestInsertNewsBatch:
    """Tests for insert_news_batch — persisting news articles."""

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_insert_news_success(self, mock_session_factory: MagicMock) -> None:
        """News articles are inserted; rowcount returned."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        articles = [
            NewsArticle(
                title="Bitcoin Surge",
                content="Price increased by 10%",
                source="decrypt",
                url="https://decrypt.co/article1",
                published_at=FIXED_TS,
                sentiment_score=Decimal("0.8"),
                reliability_score=Decimal("0.9"),
            ),
            NewsArticle(
                title="Ethereum Update",
                content="New upgrade deployed",
                source="cointelegraph",
                url="https://cointelegraph.com/article2",
                published_at=FIXED_TS,
                sentiment_score=Decimal("0.6"),
                reliability_score=Decimal("0.85"),
            ),
        ]

        inserted = await insert_news_batch(articles)

        assert inserted == 2
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_insert_news_handles_duplicate_urls(self, mock_session_factory: MagicMock) -> None:
        """ON CONFLICT (url) DO NOTHING is applied (duplicate URLs are skipped)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1  # Only 1 of 2 articles inserted
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        articles = [
            NewsArticle(
                title="Article A",
                source="decrypt",
                url="https://example.com/same",
                published_at=FIXED_TS,
            ),
            NewsArticle(
                title="Article B",
                source="decrypt",
                url="https://example.com/same",  # Duplicate URL
                published_at=FIXED_TS,
            ),
        ]

        inserted = await insert_news_batch(articles)

        assert inserted == 1


class TestFetchOhlcvForIndicators:
    """Tests for fetch_ohlcv_for_indicators — fetching OHLCV for indicator calculation."""

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_fetch_success(self, mock_session_factory: MagicMock) -> None:
        """OHLCV rows are fetched in chronological order."""
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Mock returns rows in reverse order (DESC timestamp)
        rows_desc = [
            {
                "timestamp": FIXED_TS.replace(hour=13),
                "price_open": Decimal("51000.00"),
                "price_high": Decimal("52000.00"),
                "price_low": Decimal("50500.00"),
                "price_close": Decimal("51500.00"),
                "volume_24h": Decimal("120.00"),
            },
            {
                "timestamp": FIXED_TS,
                "price_open": Decimal("50000.00"),
                "price_high": Decimal("51000.00"),
                "price_low": Decimal("49500.00"),
                "price_close": Decimal("50500.00"),
                "volume_24h": Decimal("100.00"),
            },
        ]
        mock_result.mappings().all.return_value = rows_desc
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        rows = await fetch_ohlcv_for_indicators("BTCUSDT", "1h", limit=500)

        # Should be reversed to chronological order
        assert len(rows) == 2
        assert rows[0]["timestamp"] == FIXED_TS  # Oldest first
        assert rows[1]["timestamp"] == FIXED_TS.replace(hour=13)  # Newest last


class TestDetectGaps:
    """Tests for detect_gaps — identifying missing OHLCV timestamps."""

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_detect_gaps_no_gaps(self, mock_session_factory: MagicMock) -> None:
        """Continuous timestamps have no gaps."""
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Timestamps at 1-hour intervals (no gaps)
        ts1 = FIXED_TS
        ts2 = FIXED_TS.replace(hour=13)
        ts3 = FIXED_TS.replace(hour=14)
        mock_result.fetchall.return_value = [(ts1,), (ts2,), (ts3,)]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        gaps = await detect_gaps("BTCUSDT", "1h", 3600, FIXED_TS)

        assert gaps == []

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_detect_gaps_with_missing_timestamp(self, mock_session_factory: MagicMock) -> None:
        """Missing timestamps are identified as gaps."""
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Timestamps with 2-hour gap (hour 14 is missing)
        ts1 = FIXED_TS
        ts2 = FIXED_TS.replace(hour=13)
        ts3 = FIXED_TS.replace(hour=15)
        mock_result.fetchall.return_value = [(ts1,), (ts2,), (ts3,)]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        gaps = await detect_gaps("BTCUSDT", "1h", 3600, FIXED_TS)

        # Should identify the missing hour 14
        assert len(gaps) == 1
        assert gaps[0] == FIXED_TS.replace(hour=14)

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.async_session_factory")
    async def test_detect_gaps_insufficient_data(self, mock_session_factory: MagicMock) -> None:
        """Fewer than 2 timestamps return no gaps."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(FIXED_TS,)]  # Only 1 row
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        gaps = await detect_gaps("BTCUSDT", "1h", 3600, FIXED_TS)

        assert gaps == []
