"""Unit tests for auth service."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import auth_service
from src.api.services.auth_service import ConflictError, _verify_password
from src.shared.exceptions import AuthenticationError
from src.shared.models.orm import UserOrm


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_creates_user(self, db_session: AsyncSession) -> None:
        user = await auth_service.register(db_session, "newuser", "new@example.com", "password123", "trader")
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.persona_type == "trader"
        assert _verify_password("password123", user.password_hash)

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        with pytest.raises(ConflictError):
            await auth_service.register(db_session, "other", "test@example.com", "password123", "trader")

    @pytest.mark.asyncio
    async def test_register_duplicate_username_raises(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        with pytest.raises(ConflictError):
            await auth_service.register(db_session, "testuser", "other@example.com", "password123", "trader")


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_valid(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        user = await auth_service.authenticate(db_session, "test@example.com", "testpassword123")
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        with pytest.raises(AuthenticationError):
            await auth_service.authenticate(db_session, "test@example.com", "wrongpassword")

    @pytest.mark.asyncio
    async def test_authenticate_unknown_email(self, db_session: AsyncSession) -> None:
        with pytest.raises(AuthenticationError):
            await auth_service.authenticate(db_session, "nobody@example.com", "password123")


class TestToken:
    def test_create_access_token(self) -> None:
        token = auth_service.create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        user = await auth_service.get_user_by_id(db_session, test_user.id)
        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session: AsyncSession) -> None:
        user = await auth_service.get_user_by_id(db_session, "nonexistent")
        assert user is None


class TestRefreshToken:
    """Refresh token operations."""

    @pytest.mark.asyncio
    async def test_refresh_access_token_with_valid_user(self, db_session: AsyncSession, test_user: UserOrm) -> None:
        """Refresh token with valid user succeeds."""
        token = auth_service.create_access_token(str(test_user.id))
        result_user = await auth_service.refresh_access_token(db_session, token)
        assert result_user.id == test_user.id

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, db_session: AsyncSession) -> None:
        """Refresh with invalid token raises AuthenticationError."""
        with pytest.raises(AuthenticationError):
            await auth_service.refresh_access_token(db_session, "invalid.token.here")

    @pytest.mark.asyncio
    async def test_refresh_access_token_user_not_found(self, db_session: AsyncSession) -> None:
        """Refresh with token for non-existent user raises AuthenticationError."""
        token = auth_service.create_access_token("nonexistent-user-id")
        with pytest.raises(AuthenticationError):
            await auth_service.refresh_access_token(db_session, token)
