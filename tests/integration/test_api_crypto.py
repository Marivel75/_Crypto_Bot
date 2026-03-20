"""Integration tests for /api/v1/crypto endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

_LIST_URL = "/api/v1/crypto/list"
_MARKET_URL = "/api/v1/crypto/market-overview"

_FIXED_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers — seed DB with test OHLCV data
# ---------------------------------------------------------------------------


async def _seed_prices(db_session: AsyncSession, symbol: str = "BTCUSDT", n: int = 2) -> None:
    """Insert n CryptoPriceOrm rows for the given symbol."""
    # We import the test-compatible ORM from conftest monkey-patch
    from src.shared.models.orm import CryptoPriceOrm

    for i in range(n):
        from datetime import timedelta

        ts = _FIXED_TS + timedelta(hours=i)
        row = CryptoPriceOrm(
            symbol=symbol,
            timeframe="1h",
            timestamp=ts,
            price_open=40_000.0 + i * 100,
            price_high=41_000.0 + i * 100,
            price_low=39_000.0 + i * 100,
            price_close=40_500.0 + i * 100,
            volume_24h=1000.0,
            source="binance",
        )
        db_session.add(row)
    await db_session.commit()


# ---------------------------------------------------------------------------
# GET /api/v1/crypto/list
# ---------------------------------------------------------------------------


class TestCryptoListEndpoint:
    @pytest.mark.asyncio
    async def test_list_returns_200(self, client: AsyncClient) -> None:
        response = await client.get(_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_returns_tracked_symbols(self, client: AsyncClient) -> None:
        response = await client.get(_LIST_URL)
        body = response.json()
        data = body["data"]
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_list_items_have_symbol_field(self, client: AsyncClient) -> None:
        response = await client.get(_LIST_URL)
        body = response.json()
        for item in body["data"]:
            assert "symbol" in item

    @pytest.mark.asyncio
    async def test_list_includes_btc(self, client: AsyncClient) -> None:
        response = await client.get(_LIST_URL)
        symbols = [item["symbol"] for item in response.json()["data"]]
        assert "BTC" in symbols


# ---------------------------------------------------------------------------
# GET /api/v1/crypto/{symbol}/prices
# ---------------------------------------------------------------------------


class TestCryptoPricesEndpoint:
    @pytest.mark.asyncio
    async def test_prices_returns_200_with_data(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_prices(db_session, symbol="BTCUSDT", n=3)
        response = await client.get("/api/v1/crypto/BTCUSDT/prices?timeframe=1h")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_prices_returns_seeded_records(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_prices(db_session, symbol="BTCUSDT", n=3)
        response = await client.get("/api/v1/crypto/BTCUSDT/prices?timeframe=1h")
        body = response.json()
        assert len(body["data"]) == 3

    @pytest.mark.asyncio
    async def test_prices_empty_for_unknown_symbol(self, client: AsyncClient, db_session: AsyncSession) -> None:
        response = await client.get("/api/v1/crypto/UNKNOWNSYM/prices?timeframe=1h")
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []

    @pytest.mark.asyncio
    async def test_prices_pagination_meta_present(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_prices(db_session, symbol="BTCUSDT", n=5)
        response = await client.get("/api/v1/crypto/BTCUSDT/prices?timeframe=1h&limit=2")
        body = response.json()
        assert body["meta"] is not None
        assert "total" in body["meta"]
        assert "page" in body["meta"]
        assert "limit" in body["meta"]

    @pytest.mark.asyncio
    async def test_prices_limit_respected(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_prices(db_session, symbol="BTCUSDT", n=10)
        response = await client.get("/api/v1/crypto/BTCUSDT/prices?timeframe=1h&limit=3")
        body = response.json()
        assert len(body["data"]) <= 3


# ---------------------------------------------------------------------------
# GET /api/v1/crypto/market-overview
# ---------------------------------------------------------------------------


class TestMarketOverviewEndpoint:
    @pytest.mark.asyncio
    async def test_market_overview_returns_200(self, client: AsyncClient) -> None:
        response = await client.get(_MARKET_URL)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_market_overview_has_expected_fields(self, client: AsyncClient) -> None:
        response = await client.get(_MARKET_URL)
        body = response.json()
        data = body["data"]
        assert "total_symbols" in data
        assert "top_gainers" in data
        assert "top_losers" in data

    @pytest.mark.asyncio
    async def test_market_overview_total_symbols_is_positive(self, client: AsyncClient) -> None:
        response = await client.get(_MARKET_URL)
        body = response.json()
        assert body["data"]["total_symbols"] > 0

    @pytest.mark.asyncio
    async def test_market_overview_gainers_losers_are_lists(self, client: AsyncClient) -> None:
        response = await client.get(_MARKET_URL)
        body = response.json()
        assert isinstance(body["data"]["top_gainers"], list)
        assert isinstance(body["data"]["top_losers"], list)
