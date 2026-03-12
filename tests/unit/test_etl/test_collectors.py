"""Unit tests for ETL collectors — mock all HTTP calls."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from src.etl.collectors.binance import BinanceCollector
from src.etl.collectors.coingecko import CoinGeckoCollector
from src.etl.collectors.fear_greed import FearGreedCollector

FIXED_TS = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
FIXED_MS = int(FIXED_TS.timestamp() * 1000)


class TestBinanceCollector:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_ohlcv(self) -> None:
        kline = [
            FIXED_MS,  # open time
            "50000.00",  # open
            "51000.00",  # high
            "49000.00",  # low
            "50500.00",  # close
            "100.50",  # volume
            FIXED_MS + 3600000,  # close time
            "5000000.00",  # quote asset volume
            100,  # number of trades
            "50.25",  # taker buy base
            "2500000.00",  # taker buy quote
            "0",  # ignore
        ]
        respx.get("https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=[kline]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", timeframe="1h", limit=1)
        assert len(records) == 1
        assert records[0].symbol == "BTCUSDT"
        assert float(records[0].price_open) == 50000.0

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_empty_response(self) -> None:
        respx.get("https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=[]))

        async with BinanceCollector() as collector:
            records = await collector.fetch_ohlcv("BTCUSDT", timeframe="1h", limit=1)
        assert records == []

    @pytest.mark.asyncio
    async def test_unsupported_timeframe(self) -> None:
        collector = BinanceCollector()
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            await collector.fetch_ohlcv("BTCUSDT", timeframe="invalid")


class TestCoinGeckoCollector:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_market_data(self) -> None:
        market_data = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "current_price": 50000.0,
                "high_24h": 51000.0,
                "low_24h": 49000.0,
                "total_volume": 1000000.0,
                "market_cap": 900000000000.0,
                "last_updated": "2025-06-01T12:00:00.000Z",
            }
        ]
        respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
            return_value=httpx.Response(200, json=market_data)
        )

        async with CoinGeckoCollector() as collector:
            raw = await collector.fetch_market_data(["BTC"])
        assert len(raw) == 1
        assert raw[0]["symbol"] == "btc"


class TestFearGreedCollector:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_fng(self) -> None:
        fng_data = {
            "data": [
                {
                    "value": "25",
                    "value_classification": "Extreme Fear",
                    "timestamp": str(int(FIXED_TS.timestamp())),
                }
            ]
        }
        respx.get("https://api.alternative.me/fng/").mock(return_value=httpx.Response(200, json=fng_data))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()
        assert result["value"] == 25
        assert result["value_classification"] == "Extreme Fear"
