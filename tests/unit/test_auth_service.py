"""Unit tests for auth_service — password hashing, JWT creation/decoding."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from src.api.services.auth_service import (
    ALGORITHM,
    ConflictError,
    _hash_password,
    _verify_password,
    create_access_token,
    decode_access_token,
)
from src.shared.config import settings
from src.shared.exceptions import AuthenticationError

_TEST_PASS = "T3stPw#8chars"  # noqa: S105 — test-only value, not a real credential

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        hashed = _hash_password(_TEST_PASS)
        assert hashed != _TEST_PASS

    def test_verify_correct_password(self) -> None:
        hashed = _hash_password(_TEST_PASS)
        assert _verify_password(_TEST_PASS, hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = _hash_password(_TEST_PASS)
        assert _verify_password("wrong-attempt", hashed) is False

    def test_two_hashes_of_same_password_differ(self) -> None:
        # bcrypt uses a random salt per hash
        h1 = _hash_password(_TEST_PASS)
        h2 = _hash_password(_TEST_PASS)
        assert h1 != h2


# ---------------------------------------------------------------------------
# JWT creation
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_returns_string(self) -> None:
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_payload_contains_sub(self) -> None:
        token = create_access_token("user-456")
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-456"

    def test_payload_contains_username_when_provided(self) -> None:
        token = create_access_token("user-789", username="alice")
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
        assert payload["username"] == "alice"

    def test_payload_has_expiry(self) -> None:
        token = create_access_token("user-abc")
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_expiry_is_in_future(self) -> None:
        token = create_access_token("user-future")
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
        exp = payload["exp"]
        assert exp > time.time()

    def test_no_username_key_when_not_provided(self) -> None:
        token = create_access_token("user-nousername")
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
        assert "username" not in payload


# ---------------------------------------------------------------------------
# JWT decoding
# ---------------------------------------------------------------------------


class TestDecodeAccessToken:
    def test_decode_valid_token(self) -> None:
        token = create_access_token("user-decode")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-decode"

    def test_decode_invalid_token_raises_authentication_error(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token("this.is.not.a.valid.token")

    def test_decode_tampered_token_raises_authentication_error(self) -> None:
        token = create_access_token("user-tamper")
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        with pytest.raises(AuthenticationError):
            decode_access_token(tampered)

    def test_decode_expired_token_raises_authentication_error(self) -> None:
        expire = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        payload = {"sub": "user-expired", "exp": expire}
        expired_token = jwt.encode(payload, settings.api_secret_key, algorithm=ALGORITHM)
        with pytest.raises(AuthenticationError):
            decode_access_token(expired_token)

    def test_decode_token_with_wrong_secret_raises_authentication_error(self) -> None:
        other_secret = "another-secret-value-for-test"  # noqa: S105
        wrong_token = jwt.encode(
            {"sub": "user-wrong", "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1)},
            other_secret,
            algorithm=ALGORITHM,
        )
        with pytest.raises(AuthenticationError):
            decode_access_token(wrong_token)


# ---------------------------------------------------------------------------
# register / authenticate — async DB functions (mocked session)
# ---------------------------------------------------------------------------


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_creates_user(self) -> None:
        from src.api.services.auth_service import register

        mock_user = MagicMock()
        mock_user.id = "new-user-id"
        mock_user.username = "newuser"
        mock_user.email = "new@example.com"

        db = AsyncMock()
        # No existing user found
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        # Patch select so the query construction is bypassed
        with (
            patch("src.api.services.auth_service.select", return_value=MagicMock()),
            patch("src.api.services.auth_service.UserOrm") as MockUserOrm,
        ):
            MockUserOrm.return_value = mock_user
            await register(db, "newuser", "new@example.com", _TEST_PASS, "trader")

        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_raises_conflict_if_user_exists(self) -> None:
        from src.api.services.auth_service import register

        db = AsyncMock()
        existing = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))

        with pytest.raises(ConflictError):
            await register(db, "existing", "exists@example.com", _TEST_PASS, "trader")


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials(self) -> None:
        from src.api.services.auth_service import authenticate

        hashed = _hash_password(_TEST_PASS)
        mock_user = MagicMock()
        mock_user.password_hash = hashed

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_user))

        user = await authenticate(db, "user@test.com", _TEST_PASS)
        assert user is mock_user

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password_raises(self) -> None:
        from src.api.services.auth_service import authenticate

        hashed = _hash_password(_TEST_PASS)
        mock_user = MagicMock()
        mock_user.password_hash = hashed

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_user))

        with pytest.raises(AuthenticationError):
            await authenticate(db, "user@test.com", "wrong-attempt")

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user_raises(self) -> None:
        from src.api.services.auth_service import authenticate

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        with pytest.raises(AuthenticationError):
            await authenticate(db, "nobody@test.com", "any-attempt")
