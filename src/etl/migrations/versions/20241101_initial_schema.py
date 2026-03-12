"""Initial schema — all 8 tables for the crypto-bot platform.

Revision ID: 0001
Revises: None
Create Date: 2024-11-01
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

logger = logging.getLogger(__name__)

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("persona_type", sa.String(20), nullable=True),
        sa.Column("preferences", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("persona_type IN ('trader', 'journalist', 'investor')", name="ck_users_persona_type"),
    )

    # Crypto prices (will become hypertable — composite PK required by TimescaleDB)
    op.create_table(
        "crypto_prices",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_open", sa.Numeric(20, 8), nullable=False),
        sa.Column("price_high", sa.Numeric(20, 8), nullable=False),
        sa.Column("price_low", sa.Numeric(20, 8), nullable=False),
        sa.Column("price_close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume_24h", sa.Numeric(20, 8), nullable=False),
        sa.Column("market_cap", sa.Numeric(20, 2), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timeframe", "timestamp", name="pk_crypto_prices"),
    )
    op.create_index("idx_prices_symbol_tf", "crypto_prices", ["symbol", "timeframe", "timestamp"])

    # TimescaleDB hypertable + policies (wrapped in try/except for CI without TimescaleDB)
    try:
        op.execute("SELECT create_hypertable('crypto_prices', 'timestamp', migrate_data => true)")
        op.execute("""
            ALTER TABLE crypto_prices SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'symbol, timeframe',
                timescaledb.compress_orderby = 'timestamp DESC'
            )
        """)
        op.execute("SELECT add_compression_policy('crypto_prices', INTERVAL '7 days')")
        op.execute("SELECT add_retention_policy('crypto_prices', INTERVAL '90 days', if_not_exists => true)")
        logger.info("TimescaleDB hypertable and policies created for crypto_prices")
    except Exception:
        logger.warning("TimescaleDB extension not available — skipping hypertable creation")

    # Indicators
    op.create_table(
        "indicators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rsi", sa.Numeric(10, 4), nullable=True),
        sa.Column("bollinger_upper", sa.Numeric(20, 8), nullable=True),
        sa.Column("bollinger_middle", sa.Numeric(20, 8), nullable=True),
        sa.Column("bollinger_lower", sa.Numeric(20, 8), nullable=True),
        sa.Column("price_vs_bollinger", sa.Numeric(10, 6), nullable=True),
        sa.Column("harmonic_pattern", sa.String(50), nullable=True),
        sa.Column("trend_slope", sa.Numeric(10, 6), nullable=True),
        sa.Column("trend_type", sa.String(20), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_indicators_symbol_tf_ts"),
    )

    # Trading signals
    op.create_table(
        "trading_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("signal_type", sa.String(10), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("timeframe_primary", sa.String(10), nullable=False),
        sa.Column("timeframes_aligned", JSONB, nullable=False, server_default="{}"),
        sa.Column("rules_triggered", JSONB, nullable=False, server_default="{}"),
        sa.Column("leverage_suggested", sa.Integer, nullable=True),
        sa.Column("margin_safety", sa.Numeric(10, 4), nullable=True),
        sa.Column("fees_estimated", sa.Numeric(10, 6), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("signal_type IN ('BUY', 'SELL', 'HOLD')", name="ck_trading_signals_signal_type"),
    )

    # Signal outcomes
    op.create_table(
        "signal_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "signal_id", UUID(as_uuid=True), sa.ForeignKey("trading_signals.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("price_at_signal", sa.Numeric(20, 8), nullable=True),
        sa.Column("price_after_1h", sa.Numeric(20, 8), nullable=True),
        sa.Column("price_after_4h", sa.Numeric(20, 8), nullable=True),
        sa.Column("price_after_1d", sa.Numeric(20, 8), nullable=True),
        sa.Column("pnl_simulated", sa.Numeric(10, 4), nullable=True),
        sa.Column("was_correct", sa.Boolean, nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Portfolio
    op.create_table(
        "portfolio",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Watchlist
    op.create_table(
        "watchlist",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )

    # News articles
    op.create_table(
        "news_articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("url", sa.String(1000), unique=True, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sentiment_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("keywords", JSONB, nullable=False, server_default="[]"),
        sa.Column("reliability_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Text mining results
    op.create_table(
        "text_mining_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "article_id", UUID(as_uuid=True), sa.ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("word_cloud", JSONB, nullable=False, server_default="{}"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("entities", JSONB, nullable=False, server_default="[]"),
        sa.Column("topics", JSONB, nullable=False, server_default="[]"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("text_mining_results")
    op.drop_table("news_articles")
    op.drop_table("watchlist")
    op.drop_table("portfolio")
    op.drop_table("signal_outcomes")
    op.drop_table("trading_signals")
    op.drop_table("indicators")
    op.drop_index("idx_prices_symbol_tf", table_name="crypto_prices")
    op.drop_table("crypto_prices")
    op.drop_table("users")
