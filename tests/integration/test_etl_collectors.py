"""Integration tests for ETL collectors using respx to mock HTTP calls."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from src.etl.collectors.binance import BinanceCollector
from src.etl.collectors.coingecko import CoinGeckoCollector
from src.etl.collectors.fear_greed import FearGreedCollector
from src.etl.collectors.news import NewsCollector
from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.models.crypto import NewsArticle, OHLCVRecord

# Fixed open_time: 2024-01-01 00:00:00 timezone.utc in milliseconds
_OPEN_TIME_MS = 1_704_067_200_000
_FIXED_TS_ISO = "2024-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# BinanceCollector
# ---------------------------------------------------------------------------


class TestBinanceCollector:
    def _kline_row(self, open_time_ms: int = _OPEN_TIME_MS) -> list[object]:
        return [
            open_time_ms,
            "40000.00",
            "41000.00",
            "39500.00",
            "40500.00",
            "1234.56",
            open_time_ms + 3_600_000,
            "50000000.00",
            100,
            "600.00",
            "24000000.00",
            "0",
        ]

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_ohlcv_returns_records(self) -> None:
        rows = [self._kline_row(_OPEN_TIME_MS + i * 3_600_000) for i in range(3)]
        respx.get("https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=rows))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=3)

        assert len(records) == 3
        assert all(isinstance(r, OHLCVRecord) for r in records)

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_ohlcv_parses_fields_correctly(self) -> None:
        rows = [self._kline_row()]
        respx.get("https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=rows))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        r = records[0]
        assert r.symbol == "BTCUSDT"
        assert r.source == "binance"
        assert r.timeframe == "1h"
        assert float(r.price_open) == pytest.approx(40_000.0)
        assert float(r.price_high) == pytest.approx(41_000.0)
        assert float(r.price_low) == pytest.approx(39_500.0)
        assert float(r.price_close) == pytest.approx(40_500.0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_ohlcv_rate_limit_raises(self) -> None:
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "60"})
        )

        async with BinanceCollector() as collector:
            with pytest.raises(RateLimitError):
                await collector.fetch_ohlcv("BTCUSDT", "1h")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_ohlcv_server_error_raises(self) -> None:
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        async with BinanceCollector() as collector:
            with pytest.raises(ExternalAPIError):
                await collector.fetch_ohlcv("BTCUSDT", "1h")

    @pytest.mark.asyncio
    async def test_unsupported_timeframe_raises_value_error(self) -> None:
        async with BinanceCollector() as collector:
            with pytest.raises(ValueError, match="Unsupported timeframe"):
                await collector.fetch_ohlcv("BTCUSDT", "99x")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_ohlcv_timestamp_is_utc(self) -> None:
        rows = [self._kline_row()]
        respx.get("https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=rows))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert records[0].timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# CoinGeckoCollector
# ---------------------------------------------------------------------------

_COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
_MOCK_MARKET_DATA = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 40_000,
        "market_cap": 800_000_000_000,
        "total_volume": 30_000_000_000,
    }
]


class TestCoinGeckoCollector:
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_market_data_returns_list(self) -> None:
        respx.get(_COINGECKO_MARKETS_URL).mock(return_value=httpx.Response(200, json=_MOCK_MARKET_DATA))

        async with CoinGeckoCollector() as collector:
            data = await collector.fetch_market_data(["BTC"])

        assert len(data) == 1
        assert data[0]["id"] == "bitcoin"

    @pytest.mark.asyncio
    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_market_data_rate_limit_raises(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_COINGECKO_MARKETS_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(RateLimitError):
                await collector.fetch_market_data(["BTC"])

    @pytest.mark.asyncio
    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_market_data_server_error_raises(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_COINGECKO_MARKETS_URL).mock(return_value=httpx.Response(503, text="Service Unavailable"))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(ExternalAPIError):
                await collector.fetch_market_data(["BTC"])

    @pytest.mark.asyncio
    async def test_unknown_symbol_returns_empty(self) -> None:
        async with CoinGeckoCollector() as collector:
            # No HTTP call should be made — method returns [] early
            data = await collector.fetch_market_data(["UNKNOWN_XYZ"])
        assert data == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_multiple_symbols(self) -> None:
        multi = _MOCK_MARKET_DATA + [{"id": "ethereum", "symbol": "eth", "name": "Ethereum", "current_price": 2_500}]
        respx.get(_COINGECKO_MARKETS_URL).mock(return_value=httpx.Response(200, json=multi))

        async with CoinGeckoCollector() as collector:
            data = await collector.fetch_market_data(["BTC", "ETH"])

        assert len(data) == 2


# ---------------------------------------------------------------------------
# FearGreedCollector
# ---------------------------------------------------------------------------

_FNG_URL = "https://api.alternative.me/fng/?limit=1"
_FNG_RESPONSE = {
    "data": [
        {
            "value": "42",
            "value_classification": "Fear",
            "timestamp": "1704067200",
        }
    ]
}


class TestFearGreedCollector:
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_fear_greed_returns_result(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=_FNG_RESPONSE))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 42
        assert result["value_classification"] == "Fear"
        assert isinstance(result["timestamp"], datetime)
        assert result["timestamp"].tzinfo is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_fear_greed_server_error_raises(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(500, text="error"))

        async with FearGreedCollector() as collector:
            with pytest.raises(ExternalAPIError):
                await collector.fetch_fear_greed()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_as_ohlcv_returns_ohlcv_record(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=_FNG_RESPONSE))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert len(records) == 1
        r = records[0]
        assert isinstance(r, OHLCVRecord)
        assert r.symbol == "FEAR_GREED"
        assert float(r.price_close) == 42.0

    def test_parse_response_missing_data_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            FearGreedCollector._parse_response({"data": []})

    def test_parse_response_missing_fields_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            FearGreedCollector._parse_response({"data": [{"value": "42"}]})


# ---------------------------------------------------------------------------
# NewsCollector
# ---------------------------------------------------------------------------

_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Crypto News Test</title>
    <link>https://example.com</link>
    <description>Test feed</description>
    <item>
      <title>Bitcoin Hits New High</title>
      <link>https://example.com/btc-high</link>
      <description>BTC reaches record levels.</description>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Ethereum Upgrade Complete</title>
      <link>https://example.com/eth-upgrade</link>
      <description>The latest ETH upgrade is live.</description>
      <pubDate>Tue, 02 Jan 2024 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


class TestNewsCollector:
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_returns_articles(self) -> None:
        respx.get("https://test-feed.example.com/rss").mock(
            return_value=httpx.Response(200, text=_RSS_XML, headers={"Content-Type": "application/rss+xml"})
        )

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://test-feed.example.com/rss"])

        assert len(articles) == 2
        assert all(isinstance(a, NewsArticle) for a in articles)

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_article_has_title_and_url(self) -> None:
        respx.get("https://test-feed.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://test-feed.example.com/rss"])

        assert articles[0].title == "Bitcoin Hits New High"
        assert articles[0].url == "https://example.com/btc-high"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_article_has_published_at(self) -> None:
        respx.get("https://test-feed.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://test-feed.example.com/rss"])

        assert articles[0].published_at is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_failed_feed_skipped_gracefully(self) -> None:
        """A failing feed should be logged and skipped — not raise."""
        respx.get("https://failing-feed.example.com/rss").mock(return_value=httpx.Response(500, text="Server Error"))

        async with NewsCollector() as collector:
            # Should not raise
            articles = await collector.fetch_news(sources=["https://failing-feed.example.com/rss"])

        assert articles == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_multiple_sources_combined(self) -> None:
        respx.get("https://feed1.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML))
        respx.get("https://feed2.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(
                sources=["https://feed1.example.com/rss", "https://feed2.example.com/rss"]
            )

        # 2 articles per feed × 2 feeds = 4 total
        assert len(articles) == 4

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_news_source_name_extracted_from_feed_title(self) -> None:
        respx.get("https://test-feed.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://test-feed.example.com/rss"])

        assert articles[0].source == "Crypto News Test"
