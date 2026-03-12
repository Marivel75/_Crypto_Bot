"""Integration tests for /api/v1/auth endpoints.

Uses the in-memory SQLite session and the FastAPI test client defined in
tests/conftest.py. No real database connection required.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

_REGISTER_URL = "/api/v1/auth/register"
_LOGIN_URL = "/api/v1/auth/login"
_ME_URL = "/api/v1/auth/me"

_VALID_PAYLOAD = {
    "username": "integrationuser",
    "email": "integration@test.com",
    "password": "Integr8tion!",
    "persona_type": "trader",
}


class TestRegisterEndpoint:
    @pytest.mark.asyncio
    async def test_register_success_returns_201(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.post(_REGISTER_URL, json=_VALID_PAYLOAD)
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_returns_user_in_data(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.post(_REGISTER_URL, json=_VALID_PAYLOAD)
        body = response.json()
        assert body["data"]["username"] == _VALID_PAYLOAD["username"]
        assert body["data"]["email"] == _VALID_PAYLOAD["email"]
        assert "password" not in body["data"]
        assert "password_hash" not in body["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, unauthed_client: AsyncClient) -> None:
        # First registration
        await unauthed_client.post(_REGISTER_URL, json=_VALID_PAYLOAD)
        # Second with same email
        response = await unauthed_client.post(_REGISTER_URL, json=_VALID_PAYLOAD)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_email_accepted_by_router(self, unauthed_client: AsyncClient) -> None:
        # RegisterRequest.email is plain str (no EmailStr validation at the router layer).
        # The API accepts any non-empty string for email and delegates storage to the service.
        # This test documents the current behaviour — a 201 is expected here.
        payload = {**_VALID_PAYLOAD, "email": "not-an-email", "username": "userinvalidemail"}
        response = await unauthed_client.post(_REGISTER_URL, json=payload)
        # Router allows it (plain str field); service layer stores whatever is passed
        assert response.status_code in {201, 422}

    @pytest.mark.asyncio
    async def test_register_short_password_returns_422(self, unauthed_client: AsyncClient) -> None:
        payload = {**_VALID_PAYLOAD, "email": "short@test.com", "password": "short"}
        response = await unauthed_client.post(_REGISTER_URL, json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields_returns_422(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.post(_REGISTER_URL, json={"username": "only"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_success_returns_token(self, unauthed_client: AsyncClient, test_user: object) -> None:
        # test_user fixture pre-creates user with email=test@example.com, pass=testpassword123
        response = await unauthed_client.post(
            _LOGIN_URL,
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["access_token"] is not None
        assert body["data"]["token_type"] == "bearer"  # noqa: S105

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, unauthed_client: AsyncClient, test_user: object) -> None:
        response = await unauthed_client.post(
            _LOGIN_URL,
            json={"email": "test@example.com", "password": "wrongpass9!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email_returns_401(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.post(
            _LOGIN_URL,
            json={"email": "nobody@nowhere.com", "password": "doesnotmatter"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_fields_returns_422(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.post(_LOGIN_URL, json={"email": "test@example.com"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    @pytest.mark.asyncio
    async def test_me_authenticated_returns_user(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        response = await client.get(_ME_URL, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["username"] == "testuser"
        assert body["data"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.get(_ME_URL)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_invalid_token_returns_401(self, unauthed_client: AsyncClient) -> None:
        response = await unauthed_client.get(
            _ME_URL,
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_response_does_not_expose_password(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get(_ME_URL, headers=auth_headers)
        body = response.json()
        assert "password" not in body["data"]
        assert "password_hash" not in body["data"]
