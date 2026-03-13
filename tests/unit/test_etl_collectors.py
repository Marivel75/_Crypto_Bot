"""Comprehensive unit tests for ETL collectors.

All external HTTP calls are mocked via respx. No real network traffic is made.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Fixed timezone.utc timestamp used across all tests — deterministic, never datetime.now()
FIXED_TS = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
FIXED_TS_MS = int(FIXED_TS.timestamp() * 1000)  # millisecond epoch for Binance
FIXED_TS_UNIX = int(FIXED_TS.timestamp())  # second epoch for Fear & Greed

# ---------------------------------------------------------------------------
# Realistic mock payloads
# ---------------------------------------------------------------------------

# Binance kline array: 12 elements per the public API spec.
# [open_time, open, high, low, close, volume, close_time, quote_volume,
#  num_trades, taker_buy_base, taker_buy_quote, ignore]
_BINANCE_KLINE_ROW: list[object] = [
    FIXED_TS_MS,
    "50000.00",
    "51000.00",
    "49500.00",
    "50500.00",
    "123.456",
    FIXED_TS_MS + 3_600_000,
    "6234567.89",
    342,
    "61.728",
    "3117283.94",
    "0",
]

_COINGECKO_MARKET_ITEM: dict[str, object] = {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "current_price": 50000.0,
    "market_cap": 980_000_000_000.0,
    "market_cap_rank": 1,
    "fully_diluted_valuation": 1_050_000_000_000.0,
    "total_volume": 25_000_000_000.0,
    "high_24h": 51_200.0,
    "low_24h": 49_100.0,
    "price_change_24h": 800.0,
    "price_change_percentage_24h": 1.62,
    "market_cap_change_24h": 15_000_000_000.0,
    "market_cap_change_percentage_24h": 1.55,
    "circulating_supply": 19_600_000.0,
    "total_supply": 21_000_000.0,
    "max_supply": 21_000_000.0,
    "ath": 73_750.0,
    "ath_change_percentage": -32.2,
    "ath_date": "2024-03-14T07:10:36.635Z",
    "atl": 67.81,
    "atl_change_percentage": 73614.5,
    "atl_date": "2013-07-06T00:00:00.000Z",
    "roi": None,
    "last_updated": "2025-06-01T12:00:00.000Z",
    "sparkline_in_7d": None,
}

_FEAR_GREED_PAYLOAD: dict[str, object] = {
    "name": "Fear and Greed Index",
    "data": [
        {
            "value": "42",
            "value_classification": "Fear",
            "timestamp": str(FIXED_TS_UNIX),
            "time_until_update": "3600",
        }
    ],
    "metadata": {"error": None},
}

_RSS_XML_VALID = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Decrypt</title>
    <link>https://decrypt.co</link>
    <description>Crypto news from Decrypt</description>
    <item>
      <title>Bitcoin Hits New All-Time High</title>
      <link>https://decrypt.co/news/bitcoin-ath</link>
      <description>Bitcoin surged past $100k today.</description>
      <pubDate>Sun, 01 Jun 2025 12:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Ethereum ETF Approved</title>
      <link>https://decrypt.co/news/eth-etf</link>
      <description>The SEC approved the first spot Ethereum ETF.</description>
      <pubDate>Sun, 01 Jun 2025 11:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

_RSS_XML_MISSING_FIELDS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Bad Feed</title>
    <item>
      <!-- no <title> and no <link> — should be skipped -->
      <description>Orphan entry with no title or link.</description>
    </item>
    <item>
      <title>Valid Article</title>
      <link>https://example.com/valid</link>
      <description>This one has all mandatory fields.</description>
    </item>
  </channel>
</rss>
"""

_RSS_XML_INVALID = "<<< this is not valid XML at all >>>"


# ---------------------------------------------------------------------------
# TestBinanceCollector
# ---------------------------------------------------------------------------


class TestBinanceCollector:
    """Unit tests for BinanceCollector.fetch_ohlcv."""

    # ------------------------------------------------------------------
    # Success path
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_ohlcv_success(self) -> None:
        """A 200 response with one kline row is parsed into one OHLCVRecord."""
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(200, json=[_BINANCE_KLINE_ROW])
        )

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, OHLCVRecord)
        assert rec.symbol == "BTCUSDT"
        assert rec.timeframe == "1h"
        assert rec.source == "binance"
        assert rec.price_open == Decimal("50000.00")
        assert rec.price_high == Decimal("51000.00")
        assert rec.price_low == Decimal("49500.00")
        assert rec.price_close == Decimal("50500.00")
        assert rec.volume_24h == Decimal("123.456")
        assert rec.timestamp == FIXED_TS
        assert rec.market_cap is None

    @respx.mock
    async def test_fetch_ohlcv_multiple_rows(self) -> None:
        """Multiple kline rows each produce one OHLCVRecord."""
        second_ts_ms = FIXED_TS_MS + 3_600_000
        second_row: list[object] = [
            second_ts_ms,
            "50500.00",
            "52000.00",
            "50000.00",
            "51800.00",
            "200.00",
            second_ts_ms + 3_600_000,
            "10360000.00",
            500,
            "100.00",
            "5180000.00",
            "0",
        ]
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(200, json=[_BINANCE_KLINE_ROW, second_row])
        )

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("ETHUSDT", "1h", limit=2)

        assert len(records) == 2
        assert records[0].price_open == Decimal("50000.00")
        assert records[1].price_open == Decimal("50500.00")

    @respx.mock
    async def test_fetch_ohlcv_empty_response(self) -> None:
        """An empty klines array returns an empty list without error."""
        respx.get("https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=[]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "4h", limit=500)

        assert records == []

    @respx.mock
    async def test_fetch_ohlcv_correct_query_params(self) -> None:
        """The request is made with the correct symbol, interval and limit params."""
        route = respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(200, json=[_BINANCE_KLINE_ROW])
        )

        async with BinanceCollector() as collector:
            await collector.fetch_ohlcv("SOLUSDT", "4h", limit=200)

        assert route.called
        request = route.calls.last.request
        assert "symbol=SOLUSDT" in str(request.url)
        assert "interval=4h" in str(request.url)
        assert "limit=200" in str(request.url)

    # ------------------------------------------------------------------
    # Rate-limit path
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_ohlcv_rate_limit_raises_after_retries(self) -> None:
        """HTTP 429 from Binance eventually raises RateLimitError after all retries."""
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "10"})
        )

        # Patch asyncio.sleep to avoid waiting during retries.
        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with BinanceCollector() as collector:
                with pytest.raises(RateLimitError) as exc_info:
                    await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert "rate limit" in str(exc_info.value).lower()

    @respx.mock
    async def test_fetch_ohlcv_rate_limit_detail_contains_retry_after(self) -> None:
        """RateLimitError.detail includes the Retry-After header value."""
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "30"}, json={"msg": "too many requests"})
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with BinanceCollector() as collector:
                with pytest.raises(RateLimitError) as exc_info:
                    await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert exc_info.value.detail["retry_after"] == "30"

    # ------------------------------------------------------------------
    # Timeout / transport error path
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_ohlcv_timeout_raises_external_api_error(self) -> None:
        """A network timeout eventually raises ExternalAPIError after all retries."""
        respx.get("https://api.binance.com/api/v3/klines").mock(side_effect=httpx.ConnectTimeout("timed out"))

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with BinanceCollector() as collector:
                with pytest.raises(ExternalAPIError) as exc_info:
                    await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert "binance" in str(exc_info.value).lower()

    @respx.mock
    async def test_fetch_ohlcv_read_timeout_raises_external_api_error(self) -> None:
        """A read-timeout mid-response also raises ExternalAPIError."""
        respx.get("https://api.binance.com/api/v3/klines").mock(side_effect=httpx.ReadTimeout("read timed out"))

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with BinanceCollector() as collector:
                with pytest.raises(ExternalAPIError):
                    await collector.fetch_ohlcv("BTCUSDT", "4h", limit=100)

    # ------------------------------------------------------------------
    # Other HTTP error codes
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_ohlcv_500_raises_external_api_error(self) -> None:
        """HTTP 500 from Binance raises ExternalAPIError after retries."""
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with BinanceCollector() as collector:
                with pytest.raises(ExternalAPIError) as exc_info:
                    await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert "500" in str(exc_info.value)

    # ------------------------------------------------------------------
    # Unsupported timeframe
    # ------------------------------------------------------------------

    async def test_fetch_ohlcv_unsupported_timeframe_raises_value_error(self) -> None:
        """An unrecognised timeframe string raises ValueError before any HTTP call."""
        async with BinanceCollector() as collector:
            with pytest.raises(ValueError, match="Unsupported timeframe"):
                await collector.fetch_ohlcv("BTCUSDT", "99x", limit=1)

    # ------------------------------------------------------------------
    # Static parser
    # ------------------------------------------------------------------

    def test_parse_kline_produces_correct_ohlcv_record(self) -> None:
        """_parse_kline correctly maps every field from the kline array."""
        record = BinanceCollector._parse_kline(_BINANCE_KLINE_ROW, "BTCUSDT", "1h")

        assert record.symbol == "BTCUSDT"
        assert record.timeframe == "1h"
        assert record.source == "binance"
        assert record.price_open == Decimal("50000.00")
        assert record.price_high == Decimal("51000.00")
        assert record.price_low == Decimal("49500.00")
        assert record.price_close == Decimal("50500.00")
        assert record.volume_24h == Decimal("123.456")
        assert record.timestamp.tzinfo is not None  # always tz-aware


# ---------------------------------------------------------------------------
# TestCoinGeckoCollector
# ---------------------------------------------------------------------------


class TestCoinGeckoCollector:
    """Unit tests for CoinGeckoCollector.fetch_market_data."""

    # ------------------------------------------------------------------
    # Success path
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_market_data_success(self) -> None:
        """A 200 response is returned as a list of raw dicts."""
        respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(200, json=[_COINGECKO_MARKET_ITEM])
        )

        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["BTC"])

        assert len(result) == 1
        assert result[0]["id"] == "bitcoin"
        assert result[0]["current_price"] == 50_000.0

    @respx.mock
    async def test_fetch_market_data_multiple_symbols(self) -> None:
        """Two known symbols both resolve and appear in the API request."""
        eth_item: dict[str, object] = {**_COINGECKO_MARKET_ITEM, "id": "ethereum", "symbol": "eth"}
        route = respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(200, json=[_COINGECKO_MARKET_ITEM, eth_item])
        )

        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["BTC", "ETH"])

        assert len(result) == 2
        request = route.calls.last.request
        url_str = str(request.url)
        assert "bitcoin" in url_str
        assert "ethereum" in url_str

    @respx.mock
    async def test_fetch_market_data_unknown_symbol_is_skipped(self) -> None:
        """Unknown symbols are silently skipped and do not reach the HTTP layer."""
        route = respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(200, json=[_COINGECKO_MARKET_ITEM])
        )

        async with CoinGeckoCollector() as collector:
            # FAKECOIN has no CoinGecko mapping; BTC does.
            result = await collector.fetch_market_data(["BTC", "FAKECOIN"])

        # Only BTC reaches the API; FAKECOIN is skipped without error.
        assert route.called
        request = route.calls.last.request
        assert "fakecoin" not in str(request.url).lower()
        assert len(result) == 1

    @respx.mock
    async def test_fetch_market_data_all_unknown_returns_empty(self) -> None:
        """If every symbol is unmappable, an empty list is returned without an HTTP call."""
        route = respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["UNKNOWN1", "UNKNOWN2"])

        assert result == []
        assert not route.called

    @respx.mock
    async def test_fetch_market_data_correct_query_params(self) -> None:
        """The request includes vs_currency=usd and the correct coin IDs."""
        route = respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(200, json=[_COINGECKO_MARKET_ITEM])
        )

        async with CoinGeckoCollector() as collector:
            await collector.fetch_market_data(["BTC"])

        request = route.calls.last.request
        url_str = str(request.url)
        assert "vs_currency=usd" in url_str
        assert "bitcoin" in url_str

    # ------------------------------------------------------------------
    # Rate-limit path
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_market_data_rate_limit_raises(self) -> None:
        """HTTP 429 from CoinGecko raises RateLimitError after all retries."""
        respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "60"})
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with CoinGeckoCollector() as collector:
                with pytest.raises(RateLimitError):
                    await collector.fetch_market_data(["BTC"])

    @respx.mock
    async def test_fetch_market_data_rate_limit_preserves_retry_after(self) -> None:
        """RateLimitError.detail contains the Retry-After value."""
        respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "120"})
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with CoinGeckoCollector() as collector:
                with pytest.raises(RateLimitError) as exc_info:
                    await collector.fetch_market_data(["ETH"])

        assert exc_info.value.detail["retry_after"] == "120"

    # ------------------------------------------------------------------
    # Other failures
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_market_data_500_raises_external_api_error(self) -> None:
        """HTTP 500 from CoinGecko raises ExternalAPIError after retries."""
        respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(500, text="Service Unavailable")
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with CoinGeckoCollector() as collector:
                with pytest.raises(ExternalAPIError):
                    await collector.fetch_market_data(["BTC"])

    @respx.mock
    async def test_fetch_market_data_network_error_raises(self) -> None:
        """A network-level error raises ExternalAPIError after retries."""
        respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with CoinGeckoCollector() as collector:
                with pytest.raises(ExternalAPIError):
                    await collector.fetch_market_data(["BTC"])

    # ------------------------------------------------------------------
    # Symbol resolution helper
    # ------------------------------------------------------------------

    def test_resolve_coin_ids_known_symbols(self) -> None:
        """All known internal symbols resolve to their CoinGecko IDs."""
        collector = CoinGeckoCollector()
        ids = collector._resolve_coin_ids(["BTC", "ETH", "SOL"])
        assert ids == ["bitcoin", "ethereum", "solana"]

    def test_resolve_coin_ids_case_insensitive(self) -> None:
        """Symbol lookup is case-insensitive."""
        collector = CoinGeckoCollector()
        ids = collector._resolve_coin_ids(["btc", "Eth"])
        assert "bitcoin" in ids
        assert "ethereum" in ids

    def test_resolve_coin_ids_unknown_returns_empty(self) -> None:
        """Unknown symbols produce an empty list."""
        collector = CoinGeckoCollector()
        ids = collector._resolve_coin_ids(["UNKNOWN"])
        assert ids == []


# ---------------------------------------------------------------------------
# TestNewsCollector
# ---------------------------------------------------------------------------


class TestNewsCollector:
    """Unit tests for NewsCollector.fetch_news."""

    # ------------------------------------------------------------------
    # Success path — valid RSS
    # ------------------------------------------------------------------

    @respx.mock
    async def test_scrape_success_returns_articles(self) -> None:
        """A valid RSS feed is parsed and returns the expected NewsArticle list."""
        respx.get("https://decrypt.co/feed").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://decrypt.co/feed"])

        assert len(articles) == 2
        titles = [a.title for a in articles]
        assert "Bitcoin Hits New All-Time High" in titles
        assert "Ethereum ETF Approved" in titles

    @respx.mock
    async def test_scrape_success_article_fields(self) -> None:
        """Parsed NewsArticle instances have correct field values."""
        respx.get("https://decrypt.co/feed").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://decrypt.co/feed"])

        btc_article = next(a for a in articles if "Bitcoin" in a.title)
        assert isinstance(btc_article, NewsArticle)
        assert btc_article.url == "https://decrypt.co/news/bitcoin-ath"
        assert btc_article.source == "Decrypt"
        assert btc_article.content is not None
        assert "surged" in btc_article.content
        assert btc_article.published_at is not None
        assert btc_article.published_at.tzinfo is not None  # always tz-aware

    @respx.mock
    async def test_scrape_skips_entry_without_title_or_link(self) -> None:
        """RSS entries missing title or link are silently skipped."""
        respx.get("https://example.com/feed").mock(return_value=httpx.Response(200, text=_RSS_XML_MISSING_FIELDS))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://example.com/feed"])

        # The entry with no title/link is dropped; the valid one is kept.
        assert len(articles) == 1
        assert articles[0].title == "Valid Article"

    @respx.mock
    async def test_scrape_multiple_sources_combined(self) -> None:
        """Articles from multiple feeds are combined into one list."""
        respx.get("https://feed1.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))
        respx.get("https://feed2.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(
                sources=[
                    "https://feed1.example.com/rss",
                    "https://feed2.example.com/rss",
                ]
            )

        # 2 articles per feed × 2 feeds = 4 articles total
        assert len(articles) == 4

    # ------------------------------------------------------------------
    # Invalid / malformed XML
    # ------------------------------------------------------------------

    @respx.mock
    async def test_scrape_invalid_xml_does_not_crash(self) -> None:
        """A feed that returns unparseable XML is logged and skipped; no exception raised."""
        respx.get("https://badfeed.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML_INVALID))

        async with NewsCollector() as collector:
            # Should not raise — failed feeds are caught and logged.
            articles = await collector.fetch_news(sources=["https://badfeed.example.com/rss"])

        # feedparser handles invalid XML gracefully (returns 0 entries).
        # The collector should return an empty list, not raise.
        assert isinstance(articles, list)

    @respx.mock
    async def test_scrape_one_failed_feed_does_not_affect_others(self) -> None:
        """A failing feed does not prevent successful feeds from being processed."""
        respx.get("https://good.example.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))
        respx.get("https://bad.example.com/rss").mock(return_value=httpx.Response(503, text="Service Unavailable"))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(
                sources=[
                    "https://good.example.com/rss",
                    "https://bad.example.com/rss",
                ]
            )

        # Only articles from the successful feed are returned.
        assert len(articles) == 2
        assert all(a.source == "Decrypt" for a in articles)

    # ------------------------------------------------------------------
    # HTTP error
    # ------------------------------------------------------------------

    @respx.mock
    async def test_scrape_http_error_is_logged_and_skipped(self) -> None:
        """A non-2xx HTTP response from a feed is caught and logged, not raised."""
        respx.get("https://example.com/feed").mock(return_value=httpx.Response(404, text="Not Found"))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://example.com/feed"])

        assert articles == []

    @respx.mock
    async def test_scrape_empty_feed_returns_empty_list(self) -> None:
        """A valid RSS feed with no <item> elements returns an empty list."""
        empty_rss = '<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>'
        respx.get("https://empty.example.com/rss").mock(return_value=httpx.Response(200, text=empty_rss))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=["https://empty.example.com/rss"])

        assert articles == []

    # ------------------------------------------------------------------
    # Default sources fallback
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_news_uses_default_sources_when_none_given(self) -> None:
        """When sources=None, the two default feeds (Decrypt, Cointelegraph) are used."""
        respx.get("https://decrypt.co/feed").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))
        respx.get("https://cointelegraph.com/rss").mock(return_value=httpx.Response(200, text=_RSS_XML_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=None)

        # 2 articles × 2 default feeds = 4 total
        assert len(articles) == 4

    # ------------------------------------------------------------------
    # Static parser helper
    # ------------------------------------------------------------------

    def test_parse_entry_returns_none_when_title_missing(self) -> None:
        """_parse_entry returns None when the entry has no title."""
        import feedparser  # type: ignore[import-untyped]

        feed = feedparser.parse(
            '<?xml version="1.0"?><rss version="2.0"><channel>'
            "<item><link>https://example.com</link></item>"
            "</channel></rss>"
        )
        entry = feed.entries[0]
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is None

    def test_parse_entry_returns_none_when_link_missing(self) -> None:
        """_parse_entry returns None when the entry has no link."""
        import feedparser  # type: ignore[import-untyped]

        feed = feedparser.parse(
            '<?xml version="1.0"?><rss version="2.0"><channel><item><title>Some Title</title></item></channel></rss>'
        )
        entry = feed.entries[0]
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is None

    def test_parse_entry_falls_back_to_summary_when_no_content(self) -> None:
        """When content[0] is absent, summary is used as article content."""
        import feedparser  # type: ignore[import-untyped]

        feed = feedparser.parse(
            '<?xml version="1.0"?><rss version="2.0"><channel>'
            "<item>"
            "<title>Hello</title>"
            "<link>https://example.com/hello</link>"
            "<description>Summary text here.</description>"
            "</item>"
            "</channel></rss>"
        )
        entry = feed.entries[0]
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is not None
        assert result.content == "Summary text here."


# ---------------------------------------------------------------------------
# TestFearGreedCollector
# ---------------------------------------------------------------------------


class TestFearGreedCollector:
    """Unit tests for FearGreedCollector.fetch_fear_greed."""

    # ------------------------------------------------------------------
    # Success path
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_success_returns_correct_values(self) -> None:
        """A 200 response is parsed into a FearGreedResult with correct fields."""
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(200, json=_FEAR_GREED_PAYLOAD))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 42
        assert result["value_classification"] == "Fear"
        assert result["timestamp"] == FIXED_TS

    @respx.mock
    async def test_fetch_success_timestamp_is_utc_aware(self) -> None:
        """Returned timestamp is always timezone-aware timezone.utc."""
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(200, json=_FEAR_GREED_PAYLOAD))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["timestamp"].tzinfo is not None
        assert result["timestamp"].tzinfo == timezone.utc

    @respx.mock
    async def test_fetch_extreme_fear_classification(self) -> None:
        """'Extreme Fear' classification is preserved exactly as-is."""
        payload: dict[str, object] = {
            "data": [
                {
                    "value": "10",
                    "value_classification": "Extreme Fear",
                    "timestamp": str(FIXED_TS_UNIX),
                }
            ]
        }
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(200, json=payload))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 10
        assert result["value_classification"] == "Extreme Fear"

    @respx.mock
    async def test_fetch_extreme_greed_classification(self) -> None:
        """'Extreme Greed' classification is preserved exactly as-is."""
        payload: dict[str, object] = {
            "data": [
                {
                    "value": "90",
                    "value_classification": "Extreme Greed",
                    "timestamp": str(FIXED_TS_UNIX),
                }
            ]
        }
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(200, json=payload))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 90
        assert result["value_classification"] == "Extreme Greed"

    # ------------------------------------------------------------------
    # fetch_as_ohlcv convenience method
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_as_ohlcv_returns_ohlcv_record(self) -> None:
        """fetch_as_ohlcv wraps the index value in a pseudo-OHLCVRecord."""
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(200, json=_FEAR_GREED_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, OHLCVRecord)
        assert rec.symbol == "FEAR_GREED"
        assert rec.price_open == Decimal("42")
        assert rec.price_high == Decimal("42")
        assert rec.price_low == Decimal("42")
        assert rec.price_close == Decimal("42")
        assert rec.volume_24h == Decimal("0")
        assert rec.source == "alternative.me"
        assert rec.timeframe == "1D"

    # ------------------------------------------------------------------
    # Error path — HTTP errors
    # ------------------------------------------------------------------

    @respx.mock
    async def test_fetch_error_non_200_raises_external_api_error(self) -> None:
        """A non-200 HTTP response raises ExternalAPIError after retries."""
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(503, text="Service Unavailable"))

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with FearGreedCollector() as collector:
                with pytest.raises(ExternalAPIError) as exc_info:
                    await collector.fetch_fear_greed()

        assert "503" in str(exc_info.value)

    @respx.mock
    async def test_fetch_error_500_includes_status_code(self) -> None:
        """ExternalAPIError message includes the HTTP status code."""
        respx.get("https://api.alternative.me/fng/").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with FearGreedCollector() as collector:
                with pytest.raises(ExternalAPIError) as exc_info:
                    await collector.fetch_fear_greed()

        assert "500" in str(exc_info.value)

    @respx.mock
    async def test_fetch_error_network_error_raises_external_api_error(self) -> None:
        """A network-level transport error raises ExternalAPIError after retries."""
        respx.get("https://api.alternative.me/fng/").mock(side_effect=httpx.ConnectError("connection refused"))

        with patch("src.shared.utils.asyncio.sleep", new_callable=AsyncMock):
            async with FearGreedCollector() as collector:
                with pytest.raises(ExternalAPIError):
                    await collector.fetch_fear_greed()

    # ------------------------------------------------------------------
    # Error path — malformed payload
    # ------------------------------------------------------------------

    def test_parse_response_missing_data_key_raises_value_error(self) -> None:
        """A payload without the 'data' key raises ValueError."""
        bad_payload: dict[str, object] = {"name": "Fear and Greed Index"}
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse_response(bad_payload)

    def test_parse_response_empty_data_list_raises_value_error(self) -> None:
        """A payload with an empty 'data' list raises ValueError."""
        bad_payload: dict[str, object] = {"data": []}
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse_response(bad_payload)

    def test_parse_response_missing_value_field_raises_value_error(self) -> None:
        """A data entry missing the 'value' field raises ValueError."""
        bad_payload: dict[str, object] = {
            "data": [
                {
                    "value_classification": "Fear",
                    "timestamp": str(FIXED_TS_UNIX),
                    # 'value' is intentionally absent
                }
            ]
        }
        with pytest.raises(ValueError, match="Missing required fields"):
            FearGreedCollector._parse_response(bad_payload)

    def test_parse_response_non_numeric_value_raises_value_error(self) -> None:
        """A 'value' field that cannot be cast to int raises ValueError."""
        bad_payload: dict[str, object] = {
            "data": [
                {
                    "value": "not_a_number",
                    "value_classification": "Fear",
                    "timestamp": str(FIXED_TS_UNIX),
                }
            ]
        }
        with pytest.raises(ValueError, match="Cannot parse Fear & Greed value"):
            FearGreedCollector._parse_response(bad_payload)

    def test_parse_response_non_numeric_timestamp_raises_value_error(self) -> None:
        """A 'timestamp' field that cannot be cast to int raises ValueError."""
        bad_payload: dict[str, object] = {
            "data": [
                {
                    "value": "42",
                    "value_classification": "Fear",
                    "timestamp": "not_a_timestamp",
                }
            ]
        }
        with pytest.raises(ValueError, match="Cannot parse Fear & Greed timestamp"):
            FearGreedCollector._parse_response(bad_payload)

    def test_parse_response_valid_payload_returns_correct_result(self) -> None:
        """A well-formed payload is parsed into the correct FearGreedResult."""
        result = FearGreedCollector._parse_response(_FEAR_GREED_PAYLOAD)

        assert result["value"] == 42
        assert result["value_classification"] == "Fear"
        assert result["timestamp"] == FIXED_TS
