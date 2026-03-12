"""Integration tests for auth endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_and_login_flow(self, unauthed_client: AsyncClient, db_session: AsyncSession) -> None:
        # Register
        resp = await unauthed_client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "Password123!",
                "persona_type": "investor",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["username"] == "newuser"

        # Login
        resp = await unauthed_client.post(
            "/api/v1/auth/login",
            json={"email": "new@example.com", "password": "Password123!"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    @pytest.mark.asyncio
    async def test_me_returns_current_user(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_me_without_auth_returns_401(self, unauthed_client: AsyncClient) -> None:
        resp = await unauthed_client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, unauthed_client: AsyncClient, db_session: AsyncSession) -> None:
        resp = await unauthed_client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "WrongPass1!"},
        )
        assert resp.status_code == 401
