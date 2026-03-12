"""Integration tests for watchlist endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.orm import WatchlistOrm

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seed_watchlist(db_session: AsyncSession, test_user) -> list[WatchlistOrm]:
    """Pre-populate the test user's watchlist with two symbols."""
    entries: list[WatchlistOrm] = []
    for symbol in ("BTC", "ETH"):
        entry = WatchlistOrm(user_id=test_user.id, symbol=symbol)
        db_session.add(entry)
        entries.append(entry)
    await db_session.commit()
    for e in entries:
        await db_session.refresh(e)
    return entries


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWatchlistEndpoints:
    # --- POST / (add) ---

    @pytest.mark.asyncio
    async def test_add_to_watchlist(self, client: AsyncClient) -> None:
        """POST / adds a symbol and returns the created entry."""
        resp = await client.post("/api/v1/watchlist", json={"symbol": "BTC"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["symbol"] == "BTC"
        assert "id" in data
        assert "user_id" in data
        assert "added_at" in data

    @pytest.mark.asyncio
    async def test_add_to_watchlist_symbol_uppercased(self, client: AsyncClient) -> None:
        """POST / normalises the symbol to upper-case."""
        resp = await client.post("/api/v1/watchlist", json={"symbol": "sol"})
        assert resp.status_code == 201
        assert resp.json()["data"]["symbol"] == "SOL"

    @pytest.mark.asyncio
    async def test_add_duplicate_symbol(self, client: AsyncClient) -> None:
        """POST / returns 409 when the same symbol is added twice."""
        await client.post("/api/v1/watchlist", json={"symbol": "ETH"})
        resp = await client.post("/api/v1/watchlist", json={"symbol": "ETH"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_add_duplicate_symbol_case_insensitive(self, client: AsyncClient) -> None:
        """POST / deduplication is case-insensitive (eth == ETH)."""
        await client.post("/api/v1/watchlist", json={"symbol": "ETH"})
        resp = await client.post("/api/v1/watchlist", json={"symbol": "eth"})
        assert resp.status_code == 409

    # --- GET / (list) ---

    @pytest.mark.asyncio
    async def test_get_watchlist_empty(self, client: AsyncClient) -> None:
        """GET / returns empty list when watchlist has no entries."""
        resp = await client.get("/api/v1/watchlist")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["error"] is None

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_watchlist")
    async def test_get_watchlist(self, client: AsyncClient) -> None:
        """GET / returns all watchlist entries for the authenticated user."""
        resp = await client.get("/api/v1/watchlist")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        symbols = {e["symbol"] for e in data}
        assert symbols == {"BTC", "ETH"}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_watchlist")
    async def test_get_watchlist_entry_shape(self, client: AsyncClient) -> None:
        """GET / entries carry all expected fields."""
        resp = await client.get("/api/v1/watchlist")
        assert resp.status_code == 200
        entry = resp.json()["data"][0]
        assert "id" in entry
        assert "user_id" in entry
        assert "symbol" in entry
        assert "added_at" in entry

    # --- DELETE /{symbol} (remove) ---

    @pytest.mark.asyncio
    async def test_remove_from_watchlist(self, client: AsyncClient) -> None:
        """DELETE /{symbol} removes the entry and subsequent GET reflects the change."""
        # Add
        resp = await client.post("/api/v1/watchlist", json={"symbol": "DOT"})
        assert resp.status_code == 201

        # Remove
        resp = await client.delete("/api/v1/watchlist/DOT")
        assert resp.status_code in (200, 204)

        # Verify gone
        resp = await client.get("/api/v1/watchlist")
        symbols = [e["symbol"] for e in resp.json()["data"]]
        assert "DOT" not in symbols

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_watchlist")
    async def test_remove_one_of_multiple_symbols(self, client: AsyncClient) -> None:
        """DELETE /{symbol} removes only the targeted symbol, leaving others intact."""
        resp = await client.delete("/api/v1/watchlist/BTC")
        assert resp.status_code in (200, 204)

        resp = await client.get("/api/v1/watchlist")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["symbol"] == "ETH"

    @pytest.mark.asyncio
    async def test_remove_nonexistent_symbol_returns_404(self, client: AsyncClient) -> None:
        """DELETE /{symbol} returns 404 when the symbol is not in the watchlist."""
        resp = await client.delete("/api/v1/watchlist/UNKNOWN")
        assert resp.status_code == 404

    # --- Auth guard ---

    @pytest.mark.asyncio
    async def test_watchlist_requires_auth_get(self, unauthed_client: AsyncClient) -> None:
        """GET / returns 401/403 when no valid token is provided."""
        resp = await unauthed_client.get("/api/v1/watchlist")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_watchlist_requires_auth_post(self, unauthed_client: AsyncClient) -> None:
        """POST / returns 401/403 when no valid token is provided."""
        resp = await unauthed_client.post("/api/v1/watchlist", json={"symbol": "BTC"})
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_watchlist_requires_auth_delete(self, unauthed_client: AsyncClient) -> None:
        """DELETE /{symbol} returns 401/403 when no valid token is provided."""
        resp = await unauthed_client.delete("/api/v1/watchlist/BTC")
        assert resp.status_code in (401, 403)
