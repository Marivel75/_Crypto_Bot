"""Authentication service — register, login, JWT."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from datetime import timedelta

UTC = timezone.utc

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import settings
from src.shared.exceptions import AuthenticationError, ConflictError
from src.shared.models.orm import UserOrm
from src.shared.models.user import UserCreate

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


async def register(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    persona_type: str,
) -> UserOrm:
    """Create and persist a new user account.

    Checks for duplicate email/username before inserting and catches
    any IntegrityError at flush time as a safety net.

    Args:
        db: Active async database session.
        username: Unique display name (3–100 characters).
        email: Unique email address.
        password: Plain-text password; hashed with bcrypt before storage.
        persona_type: One of ``trader``, ``journalist``, or ``investor``.

    Returns:
        Newly created and refreshed UserOrm instance.

    Raises:
        ConflictError: If the email or username is already in use.
    """
    existing = await db.execute(select(UserOrm).where((UserOrm.email == email) | (UserOrm.username == username)))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A user with this email or username already exists")

    user = UserOrm(
        username=username,
        email=email,
        password_hash=_hash_password(password),
        persona_type=persona_type,
        preferences={},
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        logger.warning("Registration failed due to duplicate email/username: %s", exc)
        raise ConflictError("Email or username already in use") from exc
    await db.refresh(user)
    return user


async def authenticate(
    db: AsyncSession,
    email: str,
    password: str,
) -> UserOrm:
    """Verify email and password, returning the authenticated user.

    Args:
        db: Active async database session.
        email: User's email address.
        password: Plain-text password to verify against the stored bcrypt hash.

    Returns:
        Authenticated UserOrm instance.

    Raises:
        AuthenticationError: If no user is found or the password does not match.
    """
    result = await db.execute(select(UserOrm).where(UserOrm.email == email))
    user = result.scalar_one_or_none()
    if user is None or not _verify_password(password, str(user.password_hash)):
        raise AuthenticationError("Invalid email or password")
    return user


def create_access_token(user_id: str, username: str = "") -> str:
    """Create a JWT access token.

    Args:
        user_id: UUID of the user (stored as ``sub`` claim).
        username: Display name included as ``username`` claim for convenience.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(tz=UTC) + timedelta(hours=settings.jwt_expiration_hours)
    payload: dict = {"sub": user_id, "exp": expire}
    if username:
        payload["username"] = username
    return jwt.encode(payload, settings.api_secret_key, algorithm=ALGORITHM)  # type: ignore[no-any-return]


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        AuthenticationError: If the token is invalid or expired.
    """
    try:
        return jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])  # type: ignore[no-any-return]
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


async def register_user(db: AsyncSession, user_data: UserCreate) -> UserOrm:
    """Register a new user from a UserCreate model.

    Args:
        db: Active async database session.
        user_data: Validated user creation payload.

    Returns:
        Newly created UserOrm instance.
    """
    return await register(
        db,
        username=user_data.username,
        email=str(user_data.email),
        password=user_data.password,
        persona_type=user_data.persona_type,
    )


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> UserOrm:
    """Authenticate by email (username field) and password.

    Args:
        db: Active async database session.
        username: The user's email address.
        password: Plain-text password to verify.

    Returns:
        Authenticated UserOrm instance.

    Raises:
        AuthenticationError: If credentials are invalid.
    """
    return await authenticate(db, email=username, password=password)


async def get_user_by_id(db: AsyncSession, user_id: str) -> UserOrm | None:
    """Fetch a user by their UUID.

    Args:
        db: Active async database session.
        user_id: UUID string of the user.

    Returns:
        UserOrm instance if found, ``None`` otherwise.
    """
    result = await db.execute(select(UserOrm).where(UserOrm.id == user_id))
    return result.scalar_one_or_none()
