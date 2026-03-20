"""Add paper trading, alert system, and new collectors tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-14
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

logger = logging.getLogger(__name__)

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # =========================================================================
    # Paper Trading Tables
    # =========================================================================

    # Paper accounts (simulated trading accounts)
    op.create_table(
        "paper_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("account_name", sa.String(100), nullable=False),
        sa.Column("initial_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("pnl_total", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("leverage_max", sa.Integer, nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("initial_balance > 0", name="ck_paper_accounts_initial_balance"),
        sa.CheckConstraint("leverage_max BETWEEN 1 AND 10", name="ck_paper_accounts_leverage"),
        sa.UniqueConstraint("user_id", "account_name", name="uq_paper_accounts_user_account"),
    )
    op.create_index("idx_paper_accounts_user", "paper_accounts", ["user_id"])

    # Paper positions (open positions in paper accounts)
    op.create_table(
        "paper_positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paper_account_id", UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("leverage_used", sa.Integer, nullable=False, server_default="1"),
        sa.Column("margin_required", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["paper_account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
        sa.CheckConstraint("quantity > 0", name="ck_paper_positions_quantity"),
        sa.CheckConstraint("entry_price > 0", name="ck_paper_positions_entry_price"),
        sa.CheckConstraint("current_price > 0", name="ck_paper_positions_current_price"),
        sa.CheckConstraint("leverage_used BETWEEN 1 AND 10", name="ck_paper_positions_leverage"),
        sa.CheckConstraint("margin_required > 0", name="ck_paper_positions_margin"),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name="ck_paper_positions_side"),
        sa.UniqueConstraint("paper_account_id", "symbol", "side", name="uq_paper_positions_account_symbol_side"),
    )
    op.create_index("idx_paper_positions_account", "paper_positions", ["paper_account_id"])
    op.create_index("idx_paper_positions_symbol", "paper_positions", ["symbol"])

    # Paper orders (limit/market orders with SL/TP)
    op.create_table(
        "paper_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paper_account_id", UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(20, 8), nullable=True),
        sa.Column("take_profit", JSONB, nullable=False, server_default="[]"),
        sa.Column("leverage", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["paper_account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["trading_signals.id"], ondelete="SET NULL"),
        sa.CheckConstraint("quantity > 0", name="ck_paper_orders_quantity"),
        sa.CheckConstraint("entry_price > 0", name="ck_paper_orders_entry_price"),
        sa.CheckConstraint("leverage BETWEEN 1 AND 10", name="ck_paper_orders_leverage"),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_paper_orders_side"),
        sa.CheckConstraint("order_type IN ('MARKET', 'LIMIT')", name="ck_paper_orders_order_type"),
        sa.CheckConstraint("status IN ('PENDING', 'FILLED', 'CANCELLED', 'REJECTED')", name="ck_paper_orders_status"),
        sa.CheckConstraint("jsonb_array_length(take_profit) <= 5", name="ck_paper_orders_tp_array"),
    )
    op.create_index("idx_paper_orders_account", "paper_orders", ["paper_account_id"])
    op.create_index("idx_paper_orders_signal", "paper_orders", ["signal_id"])
    op.create_index("idx_paper_orders_status", "paper_orders", ["status"])

    # Paper trades (historical trades, open and closed)
    op.create_table(
        "paper_trades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paper_account_id", UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("leverage", sa.Integer, nullable=False),
        sa.Column("pnl", sa.Numeric(20, 8), nullable=True),
        sa.Column("pnl_percent", sa.Numeric(10, 4), nullable=True),
        sa.Column("fees_paid", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("exit_reason", sa.String(50), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["paper_account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["paper_orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint("quantity > 0", name="ck_paper_trades_quantity"),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name="ck_paper_trades_side"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED', 'LIQUIDATED')", name="ck_paper_trades_status"),
    )
    op.create_index("idx_paper_trades_account", "paper_trades", ["paper_account_id"])
    op.create_index("idx_paper_trades_symbol", "paper_trades", ["symbol"])
    op.create_index("idx_paper_trades_status", "paper_trades", ["status"])
    op.create_index("idx_paper_trades_dates", "paper_trades", ["opened_at", "closed_at"])

    # =========================================================================
    # Alert System Tables
    # =========================================================================

    # Alert rules (user-defined + system defaults)
    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("condition", JSONB, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("channels", JSONB, nullable=False, server_default='["email"]'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "rule_type IN ('SIGNAL', 'PRICE', 'NEWS', 'PORTFOLIO', 'CUSTOM')", name="ck_alert_rules_type"
        ),
        sa.UniqueConstraint("user_id", "rule_name", name="uq_alert_rules_user_name"),
    )
    op.create_index("idx_alert_rules_user", "alert_rules", ["user_id"])
    op.create_index("idx_alert_rules_enabled", "alert_rules", ["enabled"])

    # Alert history (audit trail of sent alerts)
    op.create_table(
        "alert_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_rule_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_event", JSONB, nullable=False),
        sa.Column("alert_content", sa.Text, nullable=False),
        sa.Column("channels_sent", JSONB, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("status", sa.String(20), nullable=False, server_default="SENT"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["alert_rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('SENT', 'FAILED', 'BOUNCED')", name="ck_alert_history_status"),
    )
    op.create_index("idx_alert_history_user", "alert_history", ["user_id"])
    op.create_index("idx_alert_history_sent", "alert_history", ["sent_at"])
    op.create_index("idx_alert_history_status", "alert_history", ["status"])

    # =========================================================================
    # New Collectors Tables
    # =========================================================================

    # On-chain metrics (BTC/ETH focus)
    op.create_table(
        "onchain_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("metric_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("metric_unit", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "symbol IN ('BTC', 'ETH')",
            name="ck_onchain_metrics_symbol",
        ),
        sa.CheckConstraint(
            "metric_type IN ('WHALE_TRANSACTION', 'NETWORK_ACTIVE', 'MINER_REVENUE', 'GAS_PRICE', 'BURN_RATE', 'STAKING_RATIO')",
            name="ck_onchain_metrics_type",
        ),
    )
    op.create_index("idx_onchain_metrics_symbol", "onchain_metrics", ["symbol"])
    op.create_index("idx_onchain_metrics_type", "onchain_metrics", ["metric_type"])
    op.create_index("idx_onchain_metrics_collected", "onchain_metrics", ["collected_at"])

    # Regulatory alerts and documents
    op.create_table(
        "regulatory_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("impact_level", sa.String(20), nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "impact_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_regulatory_alerts_impact",
        ),
    )
    op.create_index("idx_regulatory_alerts_source", "regulatory_alerts", ["source"])
    op.create_index("idx_regulatory_alerts_published", "regulatory_alerts", ["published_at"])
    op.create_index("idx_regulatory_alerts_impact", "regulatory_alerts", ["impact_level"])

    logger.info("Migration 0002: Added paper trading, alert system, and collector tables")


def downgrade() -> None:
    # Remove in reverse order
    op.drop_index("idx_regulatory_alerts_impact")
    op.drop_index("idx_regulatory_alerts_published")
    op.drop_index("idx_regulatory_alerts_source")
    op.drop_table("regulatory_alerts")

    op.drop_index("idx_onchain_metrics_collected")
    op.drop_index("idx_onchain_metrics_type")
    op.drop_index("idx_onchain_metrics_symbol")
    op.drop_table("onchain_metrics")

    op.drop_index("idx_alert_history_status")
    op.drop_index("idx_alert_history_sent")
    op.drop_index("idx_alert_history_user")
    op.drop_table("alert_history")

    op.drop_index("idx_alert_rules_enabled")
    op.drop_index("idx_alert_rules_user")
    op.drop_table("alert_rules")

    op.drop_index("idx_paper_trades_dates")
    op.drop_index("idx_paper_trades_status")
    op.drop_index("idx_paper_trades_symbol")
    op.drop_index("idx_paper_trades_account")
    op.drop_table("paper_trades")

    op.drop_index("idx_paper_orders_status")
    op.drop_index("idx_paper_orders_signal")
    op.drop_index("idx_paper_orders_account")
    op.drop_table("paper_orders")

    op.drop_index("idx_paper_positions_symbol")
    op.drop_index("idx_paper_positions_account")
    op.drop_table("paper_positions")

    op.drop_index("idx_paper_accounts_user")
    op.drop_table("paper_accounts")

    logger.info("Downgrade 0002: Removed paper trading, alert system, and collector tables")
