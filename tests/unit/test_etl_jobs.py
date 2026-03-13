"""Unit tests for ETL scheduled jobs.

These tests verify that jobs collect, validate, and persist data correctly.
External APIs are mocked; no real network calls are made.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.etl.jobs import (
    job_collect_fear_greed,
    job_collect_market_data,
    job_collect_news,
    job_collect_ohlcv_all,
    job_collect_ohlcv_priority,
    job_compute_indicators,
)
from src.shared.models.crypto import NewsArticle, OHLCVRecord

logger = logging.getLogger(__name__)

FIXED_TS = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestJobCollectOhlcvPriority:
    """Tests for job_collect_ohlcv_priority — 1-min collection of top 13 symbols."""

    @pytest.mark.asyncio
    @patch("src.etl.jobs._fetch_symbol")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_success_collects_and_inserts(self, mock_insert: AsyncMock, mock_fetch_symbol: AsyncMock) -> None:
        """Job collects OHLCV from Binance and inserts valid records."""
        record = OHLCVRecord(
            symbol="BTCUSDT",
            price_open=Decimal("50000.00"),
            price_high=Decimal("51000.00"),
            price_low=Decimal("49500.00"),
            price_close=Decimal("50500.00"),
            volume_24h=Decimal("100.00"),
            timestamp=FIXED_TS,
            source="binance",
            timeframe="1m",
        )
        mock_fetch_symbol.return_value = [record]
        mock_insert.return_value = 1

        await job_collect_ohlcv_priority()

        # Verify fetch was called for multiple symbols
        assert mock_fetch_symbol.call_count >= 1
        # Verify insert was called with deduped records
        mock_insert.assert_called()

    @pytest.mark.asyncio
    @patch("src.etl.jobs._fetch_symbol")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_skips_failed_symbols(self, mock_insert: AsyncMock, mock_fetch_symbol: AsyncMock) -> None:
        """Job logs failures for individual symbols and continues."""
        # First call fails, second succeeds
        mock_fetch_symbol.side_effect = [
            Exception("API error"),
            [
                OHLCVRecord(
                    symbol="ETHUSDT",
                    price_open=Decimal("3000.00"),
                    price_high=Decimal("3100.00"),
                    price_low=Decimal("2900.00"),
                    price_close=Decimal("3050.00"),
                    volume_24h=Decimal("50.00"),
                    timestamp=FIXED_TS,
                    source="binance",
                    timeframe="1m",
                )
            ],
        ]
        mock_insert.return_value = 1

        # Should not raise
        await job_collect_ohlcv_priority()
        mock_insert.assert_called()

    @pytest.mark.asyncio
    @patch("src.etl.collectors.binance.BinanceCollector")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_empty_results_no_insert(self, mock_insert: AsyncMock, mock_binance: MagicMock) -> None:
        """Job skips insert if all fetches return empty results."""
        mock_collector = AsyncMock()
        mock_binance.return_value.__aenter__.return_value = mock_collector
        mock_collector.fetch_ohlcv.return_value = []

        await job_collect_ohlcv_priority()

        # Insert should not be called
        mock_insert.assert_not_called()


class TestJobCollectOhlcvAll:
    """Tests for job_collect_ohlcv_all — 5-min collection of all tracked symbols."""

    @pytest.mark.asyncio
    @patch("src.etl.jobs._fetch_symbol")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_collects_5m_for_all_symbols(self, mock_insert: AsyncMock, mock_fetch_symbol: AsyncMock) -> None:
        """Job collects 5-minute OHLCV for all tracked symbols."""
        record = OHLCVRecord(
            symbol="BTCUSDT",
            price_open=Decimal("50000.00"),
            price_high=Decimal("51000.00"),
            price_low=Decimal("49500.00"),
            price_close=Decimal("50500.00"),
            volume_24h=Decimal("100.00"),
            timestamp=FIXED_TS,
            source="binance",
            timeframe="5m",
        )
        mock_fetch_symbol.return_value = [record]
        mock_insert.return_value = 1

        await job_collect_ohlcv_all()

        # Verify timeframe is 5m (check the second argument to _fetch_symbol)
        calls = mock_fetch_symbol.call_args_list
        assert any(call.args[2] == "5m" or call.kwargs.get("timeframe") == "5m" for call in calls)


class TestJobCollectMarketData:
    """Tests for job_collect_market_data — CoinGecko market data collection."""

    @pytest.mark.asyncio
    @patch("src.etl.collectors.coingecko.CoinGeckoCollector")
    @patch("src.etl.loaders.minio_loader.upload_raw_json")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_collects_and_uploads(
        self, mock_insert: AsyncMock, mock_upload: AsyncMock, mock_cg: MagicMock
    ) -> None:
        """Job collects market data, uploads JSON, and inserts aggregate record."""
        mock_collector = AsyncMock()
        mock_cg.return_value.__aenter__.return_value = mock_collector
        mock_collector.fetch_market_data.return_value = [
            {
                "symbol": "btc",
                "market_cap": 1_000_000_000_000.0,
                "current_price": 50_000.0,
            },
            {
                "symbol": "eth",
                "market_cap": 200_000_000_000.0,
                "current_price": 3_000.0,
            },
        ]
        mock_upload.return_value = None
        mock_insert.return_value = 1

        await job_collect_market_data()

        # Verify upload was called
        mock_upload.assert_called_once()
        # Verify insert was called with market aggregate
        mock_insert.assert_called()

    @pytest.mark.asyncio
    @patch("src.etl.collectors.coingecko.CoinGeckoCollector")
    @patch("src.etl.loaders.minio_loader.upload_raw_json")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_handles_empty_market_data(
        self, mock_insert: AsyncMock, mock_upload: AsyncMock, mock_cg: MagicMock
    ) -> None:
        """Job handles empty market data gracefully."""
        mock_collector = AsyncMock()
        mock_cg.return_value.__aenter__.return_value = mock_collector
        mock_collector.fetch_market_data.return_value = []

        await job_collect_market_data()

        # Upload should not be called
        mock_upload.assert_not_called()


class TestJobCollectNews:
    """Tests for job_collect_news — RSS feed collection."""

    @pytest.mark.asyncio
    @patch("src.etl.collectors.news.NewsCollector")
    @patch("src.etl.loaders.timescaledb.insert_news_batch")
    async def test_collects_news(self, mock_insert: AsyncMock, mock_news: MagicMock) -> None:
        """Job collects news articles and inserts them."""
        mock_collector = AsyncMock()
        mock_news.return_value.__aenter__.return_value = mock_collector

        article = NewsArticle(
            title="Bitcoin Surges",
            content="Bitcoin price increased.",
            source="decrypt",
            url="https://decrypt.co/article",
            published_at=FIXED_TS,
            sentiment_score=Decimal("0.7"),
        )
        mock_collector.fetch_news.return_value = [article]
        mock_insert.return_value = 1

        await job_collect_news()

        mock_insert.assert_called_once()
        args = mock_insert.call_args[0][0]
        assert len(args) == 1
        assert args[0].title == "Bitcoin Surges"


class TestJobCollectFearGreed:
    """Tests for job_collect_fear_greed — Fear & Greed Index collection."""

    @pytest.mark.asyncio
    @patch("src.etl.collectors.fear_greed.FearGreedCollector")
    @patch("src.etl.loaders.timescaledb.insert_ohlcv_batch")
    async def test_collects_fear_greed(self, mock_insert: AsyncMock, mock_fg: MagicMock) -> None:
        """Job collects Fear & Greed index and inserts as pseudo-OHLCV."""
        mock_collector = AsyncMock()
        mock_fg.return_value.__aenter__.return_value = mock_collector

        record = OHLCVRecord(
            symbol="FEAR_GREED",
            price_open=Decimal("42.00"),
            price_high=Decimal("42.00"),
            price_low=Decimal("42.00"),
            price_close=Decimal("42.00"),
            volume_24h=Decimal("0.00"),
            timestamp=FIXED_TS,
            source="alternative.me",
            timeframe="1h",
        )
        mock_collector.fetch_as_ohlcv.return_value = [record]
        mock_insert.return_value = 1

        await job_collect_fear_greed()

        mock_insert.assert_called_once()


class TestJobComputeIndicators:
    """Tests for job_compute_indicators — RSI, Bollinger bands calculation."""

    @pytest.mark.asyncio
    @patch("src.etl.transformers.indicators.compute_indicators_for_symbol")
    @patch("src.etl.loaders.timescaledb.insert_indicators_batch")
    @patch("src.etl.loaders.timescaledb.fetch_ohlcv_for_indicators")
    async def test_computes_indicators(
        self,
        mock_fetch: AsyncMock,
        mock_insert: AsyncMock,
        mock_compute: MagicMock,
    ) -> None:
        """Job fetches OHLCV, computes indicators, and inserts results."""
        # Mock fetch returns 50 rows (enough for indicator calculation)
        mock_fetch.return_value = [
            {
                "timestamp": FIXED_TS,
                "price_open": Decimal("50000.00"),
                "price_high": Decimal("51000.00"),
                "price_low": Decimal("49500.00"),
                "price_close": Decimal("50500.00"),
                "volume_24h": Decimal("100.00"),
            }
        ] * 50
        # Mock compute returns some indicators
        mock_compute.return_value = [
            MagicMock(),  # Placeholder indicator record
        ]
        mock_insert.return_value = 1

        await job_compute_indicators()

        # Verify fetch was called
        mock_fetch.assert_called()
        # Verify insert was called if compute returned indicators
        mock_insert.assert_called()

    @pytest.mark.asyncio
    @patch("src.etl.loaders.timescaledb.fetch_ohlcv_for_indicators")
    @patch("src.etl.loaders.timescaledb.insert_indicators_batch")
    async def test_skips_insufficient_data(self, mock_insert: AsyncMock, mock_fetch: AsyncMock) -> None:
        """Job skips indicator computation if fewer than 20 rows available."""
        # Mock fetch returns only 5 rows (less than required 20)
        mock_fetch.return_value = [MagicMock()] * 5

        await job_compute_indicators()

        # Insert should not be called
        mock_insert.assert_not_called()
