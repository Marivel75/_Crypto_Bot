"""FastAPI dependency injection — DB session, auth."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import settings
from src.shared.database import async_session_factory
from src.shared.exceptions import AuthenticationError
from src.shared.models.orm import UserOrm

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            logger.exception("DB session error, rolling back")
            await session.rollback()
            raise


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserOrm:
    """Decode JWT and return the authenticated user.

    Args:
        token: Bearer JWT from the Authorization header.
        db: Active async database session.

    Returns:
        The authenticated UserOrm instance.

    Raises:
        AuthenticationError: If the token is invalid, expired, or the user is not found.
    """
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token: missing subject")
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    try:
        result = await db.execute(select(UserOrm).where(UserOrm.id == user_id))
    except Exception as exc:
        raise AuthenticationError("Invalid token: malformed user ID") from exc
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found")
    return user
