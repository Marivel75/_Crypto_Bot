"""SQLAlchemy ORM models matching the TimescaleDB schema.

All tables are defined here and imported by Alembic's env.py via Base.metadata.
For TimescaleDB hypertable promotion (crypto_prices), run the post-migration SQL
manually or via a separate migration step — Alembic does not support
SELECT create_hypertable() natively.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship

from src.shared.database import Base

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserOrm(Base):
    """Registered user account."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "persona_type IN ('trader', 'journalist', 'investor')",
            name="ck_users_persona_type",
        ),
    )

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    username: Column = Column(String(100), unique=True, nullable=False)
    email: Column = Column(String(255), unique=True, nullable=False)
    password_hash: Column = Column(String(255), nullable=False)
    persona_type: Column = Column(String(20), nullable=True)
    preferences: Column = Column(JSONB, nullable=False, server_default="{}")
    created_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    portfolio_entries: Mapped[list[PortfolioOrm]] = relationship(
        "PortfolioOrm", back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_entries: Mapped[list[WatchlistOrm]] = relationship(
        "WatchlistOrm", back_populates="user", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Crypto prices (TimescaleDB hypertable — partitioned by timestamp)
# ---------------------------------------------------------------------------


class CryptoPriceOrm(Base):
    """OHLCV candle data.

    This table must be promoted to a TimescaleDB hypertable after the initial
    migration runs:

        SELECT create_hypertable('crypto_prices', 'timestamp');

    Compression and retention policies must also be applied manually:

        ALTER TABLE crypto_prices SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'symbol, timeframe',
            timescaledb.compress_orderby = 'timestamp DESC'
        );
        SELECT add_compression_policy('crypto_prices', INTERVAL '7 days');
        SELECT add_retention_policy('crypto_prices', INTERVAL '90 days',
            if_not_exists => true);
    """

    __tablename__ = "crypto_prices"
    __table_args__ = (
        # Composite PK on (symbol, timeframe, timestamp) — required for hypertable.
        UniqueConstraint("symbol", "timeframe", "timestamp", name="pk_crypto_prices"),
        Index("idx_prices_symbol_tf", "symbol", "timeframe", "timestamp"),
    )

    # Hypertables cannot use a surrogate UUID PK easily; use a composite PK
    # expressed via the unique constraint above. SQLAlchemy still needs a
    # single primary_key=True column for its identity map — we use symbol here
    # and declare the compound PK via __mapper_args__ instead.
    symbol: Column = Column(String(20), primary_key=True, nullable=False)
    timeframe: Column = Column(String(10), primary_key=True, nullable=False)
    timestamp: Column = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    price_open: Column = Column(Numeric(20, 8), nullable=False)
    price_high: Column = Column(Numeric(20, 8), nullable=False)
    price_low: Column = Column(Numeric(20, 8), nullable=False)
    price_close: Column = Column(Numeric(20, 8), nullable=False)
    volume_24h: Column = Column(Numeric(20, 8), nullable=False)
    market_cap: Column = Column(Numeric(20, 2), nullable=True)
    source: Column = Column(String(50), nullable=False)


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------


class IndicatorOrm(Base):
    """Computed technical indicators per (symbol, timeframe, timestamp)."""

    __tablename__ = "indicators"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_indicators_symbol_tf_ts"),)

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    symbol: Column = Column(String(20), nullable=False)
    timeframe: Column = Column(String(10), nullable=False)
    timestamp: Column = Column(DateTime(timezone=True), nullable=False)
    rsi: Column = Column(Numeric(10, 4), nullable=True)
    bollinger_upper: Column = Column(Numeric(20, 8), nullable=True)
    bollinger_middle: Column = Column(Numeric(20, 8), nullable=True)
    bollinger_lower: Column = Column(Numeric(20, 8), nullable=True)
    price_vs_bollinger: Column = Column(Numeric(10, 6), nullable=True)
    harmonic_pattern: Column = Column(String(50), nullable=True)
    trend_slope: Column = Column(Numeric(10, 6), nullable=True)
    trend_type: Column = Column(String(20), nullable=True)
    indicator_metadata: Column = Column("metadata", JSONB, nullable=False, server_default="{}")


# ---------------------------------------------------------------------------
# Trading signals
# ---------------------------------------------------------------------------


class TradingSignalOrm(Base):
    """Informational trading signal produced by the ML engine."""

    __tablename__ = "trading_signals"
    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('BUY', 'SELL', 'HOLD')",
            name="ck_trading_signals_signal_type",
        ),
        Index("idx_signals_symbol_created", "symbol", "created_at"),
        Index("idx_signals_created", "created_at"),
    )

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    symbol: Column = Column(String(20), nullable=False)
    signal_type: Column = Column(String(10), nullable=False)
    confidence_score: Column = Column(Numeric(5, 4), nullable=False)
    timeframe_primary: Column = Column(String(10), nullable=False)
    timeframes_aligned: Column = Column(JSONB, nullable=False, server_default="{}")
    rules_triggered: Column = Column(JSONB, nullable=False, server_default="{}")
    leverage_suggested: Column = Column(Integer, nullable=True)
    margin_safety: Column = Column(Numeric(10, 4), nullable=True)
    fees_estimated: Column = Column(Numeric(10, 6), nullable=True)
    model_version: Column = Column(String(50), nullable=False)
    created_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    outcome: Mapped[SignalOutcomeOrm | None] = relationship("SignalOutcomeOrm", back_populates="signal", uselist=False)


# ---------------------------------------------------------------------------
# Signal outcomes
# ---------------------------------------------------------------------------


class SignalOutcomeOrm(Base):
    """Post-hoc evaluation of a trading signal."""

    __tablename__ = "signal_outcomes"
    __table_args__ = (
        Index("idx_outcomes_signal", "signal_id"),
        Index("idx_outcomes_correct", "was_correct"),
    )

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    signal_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("trading_signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_at_signal: Column = Column(Numeric(20, 8), nullable=True)
    price_after_1h: Column = Column(Numeric(20, 8), nullable=True)
    price_after_4h: Column = Column(Numeric(20, 8), nullable=True)
    price_after_1d: Column = Column(Numeric(20, 8), nullable=True)
    pnl_simulated: Column = Column(Numeric(10, 4), nullable=True)
    was_correct: Column = Column(Boolean, nullable=True)
    evaluated_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    signal: Mapped[TradingSignalOrm] = relationship("TradingSignalOrm", back_populates="outcome")


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


class PortfolioOrm(Base):
    """User portfolio position."""

    __tablename__ = "portfolio"
    __table_args__ = (Index("idx_portfolio_user", "user_id"),)

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Column = Column(String(20), nullable=False)
    quantity: Column = Column(Numeric(20, 8), nullable=False)
    entry_price: Column = Column(Numeric(20, 8), nullable=False)
    current_price: Column = Column(Numeric(20, 8), nullable=True)
    notes: Column = Column(Text, nullable=True)
    created_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )
    updated_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    user: Mapped[UserOrm] = relationship("UserOrm", back_populates="portfolio_entries")


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


class WatchlistOrm(Base):
    """User-defined symbol watchlist."""

    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),)

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Column = Column(String(20), nullable=False)
    added_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    user: Mapped[UserOrm] = relationship("UserOrm", back_populates="watchlist_entries")


# ---------------------------------------------------------------------------
# News articles
# ---------------------------------------------------------------------------


class NewsArticleOrm(Base):
    """Scraped or API-fetched news article."""

    __tablename__ = "news_articles"
    __table_args__ = (
        Index("idx_news_published", "published_at"),
        Index("idx_news_source", "source"),
    )

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    title: Column = Column(String(500), nullable=False)
    content: Column = Column(Text, nullable=True)
    source: Column = Column(String(100), nullable=False)
    url: Column = Column(String(1000), unique=True, nullable=False)
    published_at: Column = Column(DateTime(timezone=True), nullable=True)
    sentiment_score: Column = Column(Numeric(5, 4), nullable=True)
    keywords: Column = Column(JSONB, nullable=False, server_default="[]")
    reliability_score: Column = Column(Numeric(5, 4), nullable=True)
    collected_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    text_mining_result: Mapped[TextMiningResultOrm | None] = relationship(
        "TextMiningResultOrm", back_populates="article", uselist=False
    )


# ---------------------------------------------------------------------------
# Text mining results
# ---------------------------------------------------------------------------


class TextMiningResultOrm(Base):
    """NLP processing results for a news article."""

    __tablename__ = "text_mining_results"

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    article_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    word_cloud: Column = Column(JSONB, nullable=False, server_default="{}")
    summary: Column = Column(Text, nullable=True)
    entities: Column = Column(JSONB, nullable=False, server_default="[]")
    topics: Column = Column(JSONB, nullable=False, server_default="[]")
    processed_at: Column = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    article: Mapped[NewsArticleOrm] = relationship("NewsArticleOrm", back_populates="text_mining_result")


# Resolve forward references for type checkers
__all__ = [
    "Base",
    "UserOrm",
    "CryptoPriceOrm",
    "IndicatorOrm",
    "TradingSignalOrm",
    "SignalOutcomeOrm",
    "PortfolioOrm",
    "WatchlistOrm",
    "NewsArticleOrm",
    "TextMiningResultOrm",
]
