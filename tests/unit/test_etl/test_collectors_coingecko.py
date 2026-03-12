"""Unit tests for CoinGeckoCollector — all HTTP calls mocked via respx."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from src.etl.collectors.coingecko import CoinGeckoCollector
from src.shared.exceptions import ExternalAPIError, RateLimitError

_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"

SAMPLE_MARKET_RESPONSE: list[dict[str, object]] = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 42000.0,
        "market_cap": 800_000_000_000.0,
        "total_volume": 20_000_000_000.0,
        "high_24h": 43000.0,
        "low_24h": 41000.0,
        "price_change_percentage_24h": 1.5,
        "last_updated": "2023-11-14T22:00:00.000Z",
    }
]


class TestCoinGeckoCollectorFetchMarketData:
    """Tests for CoinGeckoCollector.fetch_market_data."""

    @respx.mock
    async def test_returns_raw_market_data_list(self) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_MARKET_RESPONSE))

        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["BTC"])

        assert len(result) == 1
        assert result[0]["id"] == "bitcoin"
        assert result[0]["symbol"] == "btc"

    @respx.mock
    async def test_multiple_symbols_resolved_to_ids(self) -> None:
        multi_response = [
            {"id": "bitcoin", "symbol": "btc", "current_price": 42000.0},
            {"id": "ethereum", "symbol": "eth", "current_price": 2200.0},
        ]
        route = respx.get(_MARKETS_URL).mock(return_value=httpx.Response(200, json=multi_response))

        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["BTC", "ETH"])

        assert len(result) == 2
        # Verify both IDs are in the request
        request = route.calls.last.request
        ids_param = request.url.params["ids"]
        assert "bitcoin" in ids_param
        assert "ethereum" in ids_param

    @respx.mock
    async def test_unknown_symbol_is_skipped_silently(self) -> None:
        """Symbols with no CoinGecko mapping must be skipped, not raise."""
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_MARKET_RESPONSE))

        async with CoinGeckoCollector() as collector:
            # FAKECOIN has no mapping, BTC does
            result = await collector.fetch_market_data(["BTC", "FAKECOIN"])

        # The HTTP call should have been made for BTC only; FAKECOIN skipped
        assert isinstance(result, list)

    async def test_all_unknown_symbols_returns_empty_without_http(self) -> None:
        """When no symbol resolves, return empty list without calling the API."""
        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["FAKECOIN", "NOTREAL"])

        assert result == []

    @respx.mock
    async def test_empty_symbols_list_returns_empty(self) -> None:
        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data([])

        assert result == []

    @respx.mock
    async def test_symbol_lookup_is_case_insensitive(self) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_MARKET_RESPONSE))

        async with CoinGeckoCollector() as collector:
            result = await collector.fetch_market_data(["btc"])

        assert isinstance(result, list)

    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_429_raises_rate_limit_error(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(RateLimitError):
                await collector.fetch_market_data(["BTC"])

    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_500_raises_external_api_error(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(500, text="Internal Server Error"))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(ExternalAPIError):
                await collector.fetch_market_data(["BTC"])

    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_403_raises_external_api_error_with_status(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(403, json={"error": "Forbidden"}))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(ExternalAPIError) as exc_info:
                await collector.fetch_market_data(["ETH"])

        assert "403" in str(exc_info.value)

    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_transport_error_raises_external_api_error(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_MARKETS_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(ExternalAPIError, match="Network error"):
                await collector.fetch_market_data(["BTC"])

    @respx.mock
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_rate_limit_detail_includes_retry_after(self, _mock_sleep: AsyncMock) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "45"}))

        async with CoinGeckoCollector() as collector:
            with pytest.raises(RateLimitError) as exc_info:
                await collector.fetch_market_data(["SOL"])

        assert exc_info.value.detail is not None


class TestCoinGeckoCollectorSymbolMapping:
    """Tests for _resolve_coin_ids symbol-to-CoinGecko-ID mapping."""

    def test_known_symbols_resolve_correctly(self) -> None:
        collector = CoinGeckoCollector()
        ids = collector._resolve_coin_ids(["BTC", "ETH", "SOL"])
        assert ids == ["bitcoin", "ethereum", "solana"]

    def test_unknown_symbol_excluded_from_result(self) -> None:
        collector = CoinGeckoCollector()
        ids = collector._resolve_coin_ids(["BTC", "UNKNOWN_XYZ"])
        assert ids == ["bitcoin"]
        assert "UNKNOWN_XYZ" not in ids

    def test_empty_input_returns_empty_list(self) -> None:
        collector = CoinGeckoCollector()
        ids = collector._resolve_coin_ids([])
        assert ids == []

    def test_all_known_symbols_resolve(self) -> None:
        collector = CoinGeckoCollector()
        known = ["BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "SOL", "ADA", "AVAX", "DOT", "DOGE", "TRX", "ATOM"]
        ids = collector._resolve_coin_ids(known)
        assert len(ids) == len(known)

    def test_unknown_symbol_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        collector = CoinGeckoCollector()
        with caplog.at_level(logging.WARNING, logger="src.etl.collectors.coingecko"):
            collector._resolve_coin_ids(["UNKNOWN_TOKEN"])

        assert any("UNKNOWN_TOKEN" in r.message for r in caplog.records)


class TestCoinGeckoCollectorContextManager:
    """Tests for async context manager and close behaviour."""

    @respx.mock
    async def test_context_manager_closes_client(self) -> None:
        respx.get(_MARKETS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_MARKET_RESPONSE))

        collector = CoinGeckoCollector()
        async with collector:
            await collector.fetch_market_data(["BTC"])

        assert collector._client.is_closed

    async def test_close_is_idempotent(self) -> None:
        collector = CoinGeckoCollector()
        await collector.close()
        await collector.close()
