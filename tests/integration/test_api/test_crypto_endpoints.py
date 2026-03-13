"""Integration tests for crypto endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.orm import OHLCVOrm


@pytest.fixture
async def seed_ohlcv(db_session: AsyncSession) -> None:
    """Insert sample OHLCV data."""
    for i in range(3):
        record = OHLCVOrm(
            symbol="BTC",
            timeframe="1h",
            timestamp=datetime(2025, 1, 1, i, tzinfo=timezone.utc),
            price_open=50000.0 + i * 100,
            price_high=50500.0 + i * 100,
            price_low=49500.0 + i * 100,
            price_close=50200.0 + i * 100,
            volume_24h=1000000.0,
            source="binance",
        )
        db_session.add(record)
    await db_session.commit()


class TestCryptoEndpoints:
    @pytest.mark.asyncio
    async def test_list_tracked(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/crypto/list")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) > 0
        assert data[0]["symbol"] == "BTC"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_ohlcv")
    async def test_get_prices(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/crypto/BTC/prices?timeframe=1h")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 3
        assert data["meta"]["total"] == 3

    @pytest.mark.asyncio
    async def test_get_prices_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/crypto/UNKNOWN/prices")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_ohlcv")
    async def test_get_latest(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/crypto/BTC/latest")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["symbol"] == "BTC"
        assert data["ohlcv"] is not None

    @pytest.mark.asyncio
    async def test_market_overview(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/crypto/market-overview")
        assert resp.status_code == 200
        assert "total_symbols" in resp.json()["data"]
