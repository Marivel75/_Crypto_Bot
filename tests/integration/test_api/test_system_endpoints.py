"""Integration tests for system endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestSystemEndpoints:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "ok"
        assert data["database"] == "ok"

    @pytest.mark.asyncio
    async def test_sources_status(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/system/sources-status")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
