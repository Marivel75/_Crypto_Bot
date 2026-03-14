"""Shared test fixtures — in-memory SQLite async engine."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, String
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.api.dependencies import get_current_user, get_db
from src.api.services.auth_service import create_access_token


# SQLite-compatible test Base (avoids PostgreSQL-specific types in db_models)
class TestBase(DeclarativeBase):
    """Separate declarative base for test-only models."""


# We re-define minimal ORM models with SQLite-compatible types for tests.
# This avoids importing db_models.py which uses JSONB/UUID.
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint  # noqa: E402
from sqlalchemy.orm import Mapped, relationship  # noqa: E402


def _uuid() -> str:
    import uuid

    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class UserOrm(TestBase):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=_uuid)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    persona_type = Column(String(20), nullable=True)
    preferences = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    portfolio_entries: Mapped[list[PortfolioOrm]] = relationship(
        "PortfolioOrm", back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_entries: Mapped[list[WatchlistOrm]] = relationship(
        "WatchlistOrm", back_populates="user", cascade="all, delete-orphan"
    )


class CryptoPriceOrm(TestBase):
    __tablename__ = "crypto_prices"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "timestamp", name="pk_crypto_prices"),)
    symbol = Column(String(20), primary_key=True)
    timeframe = Column(String(10), primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    price_open = Column(Float, nullable=False)
    price_high = Column(Float, nullable=False)
    price_low = Column(Float, nullable=False)
    price_close = Column(Float, nullable=False)
    volume_24h = Column(Float, nullable=False)
    market_cap = Column(Float, nullable=True)
    source = Column(String(50), nullable=False)


class IndicatorOrm(TestBase):
    __tablename__ = "indicators"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_indicators_symbol_tf_ts"),)
    id = Column(String(36), primary_key=True, default=_uuid)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    rsi = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_middle = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    price_vs_bollinger = Column(Float, nullable=True)
    harmonic_pattern = Column(String(50), nullable=True)
    trend_slope = Column(Float, nullable=True)
    trend_type = Column(String(20), nullable=True)
    indicator_metadata = Column("metadata", JSON, nullable=True, default=dict)


class TradingSignalOrm(TestBase):
    __tablename__ = "trading_signals"
    id = Column(String(36), primary_key=True, default=_uuid)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    confidence_score = Column(Float, nullable=False)
    timeframe_primary = Column(String(10), nullable=False)
    timeframes_aligned = Column(JSON, nullable=True, default=dict)
    rules_triggered = Column(JSON, nullable=True, default=list)
    leverage_suggested = Column(Integer, nullable=True)
    margin_safety = Column(Float, nullable=True)
    fees_estimated = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    outcome: Mapped[SignalOutcomeOrm | None] = relationship("SignalOutcomeOrm", back_populates="signal", uselist=False)


class SignalOutcomeOrm(TestBase):
    __tablename__ = "signal_outcomes"
    id = Column(String(36), primary_key=True, default=_uuid)
    signal_id = Column(String(36), ForeignKey("trading_signals.id"), nullable=False)
    price_at_signal = Column(Float, nullable=True)
    price_after_1h = Column(Float, nullable=True)
    price_after_4h = Column(Float, nullable=True)
    price_after_1d = Column(Float, nullable=True)
    pnl_simulated = Column(Float, nullable=True)
    was_correct = Column(Boolean, nullable=True)
    evaluated_at = Column(DateTime, nullable=False, default=_utcnow)
    signal: Mapped[TradingSignalOrm] = relationship("TradingSignalOrm", back_populates="outcome")


class PortfolioOrm(TestBase):
    __tablename__ = "portfolio"
    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    user: Mapped[UserOrm] = relationship("UserOrm", back_populates="portfolio_entries")


class WatchlistOrm(TestBase):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),)
    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    added_at = Column(DateTime, nullable=False, default=_utcnow)
    user: Mapped[UserOrm] = relationship("UserOrm", back_populates="watchlist_entries")


class NewsArticleOrm(TestBase):
    __tablename__ = "news_articles"
    id = Column(String(36), primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    published_at = Column(DateTime, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    keywords = Column(JSON, nullable=True, default=list)
    reliability_score = Column(Float, nullable=True)
    collected_at = Column(DateTime, nullable=False, default=_utcnow)


class TextMiningResultOrm(TestBase):
    __tablename__ = "text_mining_results"
    id = Column(String(36), primary_key=True, default=_uuid)
    article_id = Column(String(36), ForeignKey("news_articles.id"), nullable=False)
    word_cloud = Column(JSON, nullable=True, default=dict)
    summary = Column(Text, nullable=True)
    entities = Column(JSON, nullable=True, default=list)
    topics = Column(JSON, nullable=True, default=list)
    processed_at = Column(DateTime, nullable=False, default=_utcnow)
    article: Mapped[NewsArticleOrm] = relationship("NewsArticleOrm", backref="text_mining_result")


# Monkey-patch orm.py to use our test-compatible models
import src.shared.models.orm as orm_module  # noqa: E402

orm_module.UserOrm = UserOrm  # type: ignore[misc]
orm_module.OHLCVOrm = CryptoPriceOrm  # type: ignore[misc]
orm_module.CryptoPriceOrm = CryptoPriceOrm  # type: ignore[misc]
orm_module.IndicatorOrm = IndicatorOrm  # type: ignore[misc]
orm_module.TradingSignalOrm = TradingSignalOrm  # type: ignore[misc]
orm_module.SignalOutcomeOrm = SignalOutcomeOrm  # type: ignore[misc]
orm_module.PortfolioOrm = PortfolioOrm  # type: ignore[misc]
orm_module.PortfolioEntryOrm = PortfolioOrm  # type: ignore[misc]
orm_module.WatchlistOrm = WatchlistOrm  # type: ignore[misc]
orm_module.WatchlistEntryOrm = WatchlistOrm  # type: ignore[misc]
orm_module.NewsArticleOrm = NewsArticleOrm  # type: ignore[misc]

# Also patch service modules that already imported the original ORM classes
import src.api.dependencies as _deps  # noqa: E402
import src.api.routers.system as _system_router  # noqa: E402
import src.api.services.auth_service as _auth_svc  # noqa: E402
import src.api.services.crypto_service as _crypto_svc  # noqa: E402
import src.api.services.news_service as _news_svc  # noqa: E402
import src.api.services.signal_service as _signal_svc  # noqa: E402
import src.api.services.user_data_service as _user_svc  # noqa: E402

_auth_svc.UserOrm = UserOrm  # type: ignore[misc]
_crypto_svc.OHLCVOrm = CryptoPriceOrm  # type: ignore[misc]
_crypto_svc.IndicatorOrm = IndicatorOrm  # type: ignore[misc]
_signal_svc.TradingSignalOrm = TradingSignalOrm  # type: ignore[misc]
_signal_svc.SignalOutcomeOrm = SignalOutcomeOrm  # type: ignore[misc]
_news_svc.NewsArticleOrm = NewsArticleOrm  # type: ignore[misc]
_user_svc.PortfolioEntryOrm = PortfolioOrm  # type: ignore[misc]
_user_svc.WatchlistEntryOrm = WatchlistOrm  # type: ignore[misc]
_deps.UserOrm = UserOrm  # type: ignore[misc]
_system_router.OHLCVOrm = CryptoPriceOrm  # type: ignore[misc]

import src.api.routers.auth as _auth_router  # noqa: E402
import src.api.routers.chat as _chat_router  # noqa: E402
import src.api.routers.portfolio as _portfolio_router  # noqa: E402
import src.api.routers.watchlist as _watchlist_router  # noqa: E402
import src.api.services.chat_service as _chat_svc  # noqa: E402

_chat_svc.PortfolioEntryOrm = PortfolioOrm  # type: ignore[misc]
_chat_svc.TradingSignalOrm = TradingSignalOrm  # type: ignore[misc]
_chat_svc.WatchlistEntryOrm = WatchlistOrm  # type: ignore[misc]
_auth_router.UserOrm = UserOrm  # type: ignore[misc]
_portfolio_router.UserOrm = UserOrm  # type: ignore[misc]
_watchlist_router.UserOrm = UserOrm  # type: ignore[misc]
_chat_router.UserOrm = UserOrm  # type: ignore[misc]

# In-memory SQLite for tests
TEST_ENGINE = create_async_engine("sqlite+aiosqlite://", echo=False)
TestSessionFactory = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create tables and yield a session, then drop everything."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)

    async with TestSessionFactory() as session:
        yield session

    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> UserOrm:
    """Insert and return a test user."""
    import bcrypt

    user = UserOrm(
        id="00000000-0000-0000-0000-000000000001",
        username="testuser",
        email="test@example.com",
        password_hash=bcrypt.hashpw(b"testpassword123", bcrypt.gensalt()).decode("utf-8"),
        persona_type="trader",
        preferences={},
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: UserOrm) -> dict[str, str]:
    """Return Authorization headers with a valid JWT."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: UserOrm) -> AsyncGenerator[AsyncClient, None]:
    """Yield an httpx AsyncClient wired to the test database."""
    from src.api.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_current_user() -> UserOrm:
        return test_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthed_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Yield an httpx AsyncClient without auth override."""
    from src.api.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
