"""Unit tests for BinanceCollector — all HTTP calls mocked via respx."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
import respx

from src.etl.collectors.binance import BinanceCollector
from src.shared.exceptions import ExternalAPIError, RateLimitError

# ---------------------------------------------------------------------------
# Fixed test data
# ---------------------------------------------------------------------------

FIXED_TS = datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)
FIXED_OPEN_TIME_MS = int(FIXED_TS.timestamp() * 1000)  # 1700000000000

SAMPLE_KLINE: list[object] = [
    FIXED_OPEN_TIME_MS,  # open time (ms)
    "42000.50",  # open
    "42500.00",  # high
    "41800.25",  # low
    "42200.75",  # close
    "1234.56",  # volume
    FIXED_OPEN_TIME_MS + 3_600_000,  # close time
    "50000000.00",  # quote asset volume
    100,  # number of trades
    "600.00",  # taker buy base volume
    "25000000.00",  # taker buy quote volume
    "0",  # ignore
]

_KLINES_URL = "https://api.binance.com/api/v3/klines"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBinanceCollectorFetchOhlcv:
    """Tests for BinanceCollector.fetch_ohlcv."""

    @respx.mock
    async def test_returns_ohlcv_records_from_valid_response(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert len(records) == 1
        record = records[0]
        assert record.symbol == "BTCUSDT"
        assert record.timeframe == "1h"
        assert record.source == "binance"

    @respx.mock
    async def test_kline_decimal_conversion_is_exact(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        r = records[0]
        assert r.price_open == Decimal("42000.50")
        assert r.price_high == Decimal("42500.00")
        assert r.price_low == Decimal("41800.25")
        assert r.price_close == Decimal("42200.75")
        assert r.volume_24h == Decimal("1234.56")

    @respx.mock
    async def test_kline_timestamp_is_correct_utc(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert records[0].timestamp == FIXED_TS

    @respx.mock
    async def test_market_cap_is_none_for_binance(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert records[0].market_cap is None

    @respx.mock
    async def test_empty_kline_list_returns_empty_records(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=500)

        assert records == []

    @respx.mock
    async def test_multiple_klines_returns_multiple_records(self) -> None:
        kline2 = list(SAMPLE_KLINE)
        kline2[0] = FIXED_OPEN_TIME_MS + 3_600_000  # next candle
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE, kline2]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=2)

        assert len(records) == 2

    @respx.mock
    async def test_429_raises_rate_limit_error(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}))

        async with BinanceCollector() as collector:
            with pytest.raises(RateLimitError):
                await collector.fetch_ohlcv("BTCUSDT", "1h")

    @respx.mock
    async def test_500_raises_external_api_error(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(500, text="Internal Server Error"))

        async with BinanceCollector() as collector:
            with pytest.raises(ExternalAPIError):
                await collector.fetch_ohlcv("BTCUSDT", "1h")

    @respx.mock
    async def test_400_raises_external_api_error(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(400, json={"code": -1121, "msg": "Invalid symbol"}))

        async with BinanceCollector() as collector:
            with pytest.raises(ExternalAPIError) as exc_info:
                await collector.fetch_ohlcv("BTCUSDT", "1h")

        assert "400" in str(exc_info.value)


class TestBinanceCollectorUnsupportedTimeframe:
    """Tests for timeframe validation logic."""

    async def test_unsupported_timeframe_raises_value_error(self) -> None:
        async with BinanceCollector() as collector:
            with pytest.raises(ValueError, match="Unsupported timeframe"):
                await collector.fetch_ohlcv("BTCUSDT", "invalid_tf")

    async def test_unsupported_timeframe_lists_valid_values(self) -> None:
        async with BinanceCollector() as collector:
            with pytest.raises(ValueError, match="1h"):
                await collector.fetch_ohlcv("BTCUSDT", "bad")

    @respx.mock
    async def test_1D_maps_to_1d_binance_interval(self) -> None:
        """Internal '1D' timeframe must map to Binance interval '1d'."""
        route = respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            await collector.fetch_ohlcv("BTCUSDT", "1D", limit=1)

        assert route.called
        request = route.calls.last.request
        assert request.url.params["interval"] == "1d"

    @respx.mock
    async def test_1W_maps_to_1w_binance_interval(self) -> None:
        route = respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            await collector.fetch_ohlcv("BTCUSDT", "1W", limit=1)

        request = route.calls.last.request
        assert request.url.params["interval"] == "1w"

    @pytest.mark.parametrize("timeframe", ["1m", "5m", "1h", "2h", "3h", "4h", "1D", "1W", "1M"])
    @respx.mock
    async def test_all_supported_timeframes_do_not_raise(self, timeframe: str) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", timeframe, limit=1)

        assert isinstance(records, list)


class TestBinanceCollectorNetworkError:
    """Tests for transport-level failures."""

    @respx.mock
    async def test_transport_error_raises_external_api_error(self) -> None:
        respx.get(_KLINES_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

        async with BinanceCollector() as collector:
            with pytest.raises(ExternalAPIError, match="Network error"):
                await collector.fetch_ohlcv("BTCUSDT", "1h")

    @respx.mock
    async def test_rate_limit_detail_contains_retry_after(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))

        async with BinanceCollector() as collector:
            with pytest.raises(RateLimitError) as exc_info:
                await collector.fetch_ohlcv("BTCUSDT", "4h")

        assert exc_info.value.detail is not None


class TestBinanceCollectorContextManager:
    """Tests for async context manager and close behaviour."""

    @respx.mock
    async def test_context_manager_closes_client(self) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        collector = BinanceCollector()
        async with collector:
            records = await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        assert len(records) == 1
        # After exiting context, the underlying client should be closed
        assert collector._client.is_closed

    async def test_close_is_idempotent(self) -> None:
        collector = BinanceCollector()
        await collector.close()
        # Second close should not raise
        await collector.close()


class TestBinanceCollectorLogging:
    """Verify logging calls without asserting exact format."""

    @respx.mock
    async def test_fetch_ohlcv_emits_info_log(self, caplog: pytest.LogCaptureFixture) -> None:
        respx.get(_KLINES_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_KLINE]))

        with caplog.at_level(logging.INFO, logger="src.etl.collectors.binance"):
            async with BinanceCollector() as collector:
                await collector.fetch_ohlcv("BTCUSDT", "1h", limit=1)

        messages = [r.message for r in caplog.records]
        assert any("BTCUSDT" in m for m in messages)
