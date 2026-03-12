"""Integration tests for portfolio endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestPortfolioEndpoints:
    @pytest.mark.asyncio
    async def test_portfolio_crud_flow(self, client: AsyncClient) -> None:
        # Create
        resp = await client.post(
            "/api/v1/portfolio",
            json={"symbol": "BTC", "quantity": 0.5, "entry_price": 50000.0},
        )
        assert resp.status_code == 201
        entry = resp.json()["data"]
        entry_id = entry["id"]
        assert entry["symbol"] == "BTC"
        assert entry["quantity"] == 0.5

        # Read
        resp = await client.get("/api/v1/portfolio")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

        # Update
        resp = await client.put(
            f"/api/v1/portfolio/{entry_id}",
            json={"quantity": 1.0},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["quantity"] == 1.0

        # Delete
        resp = await client.delete(f"/api/v1/portfolio/{entry_id}")
        assert resp.status_code == 200

        # Verify deleted
        resp = await client.get("/api/v1/portfolio")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/v1/portfolio/00000000-0000-0000-0000-000000000099")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_portfolio_requires_auth(self, unauthed_client: AsyncClient) -> None:
        resp = await unauthed_client.get("/api/v1/portfolio")
        assert resp.status_code in (401, 403)
