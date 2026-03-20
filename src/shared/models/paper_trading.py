"""Pydantic models for paper trading engine."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PaperAccountCreate(BaseModel):
    """Input model for creating a paper trading account."""

    account_name: str = Field(..., min_length=1, max_length=100)
    initial_balance: Decimal = Field(..., gt=0, decimal_places=8)
    leverage_max: int = Field(default=10, ge=1, le=10)

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        """Validate account name is not empty."""
        if not v.strip():
            raise ValueError("Account name cannot be empty")
        return v.strip()


class PaperAccountRead(BaseModel):
    """Response model for paper trading account."""

    id: UUID
    user_id: UUID
    account_name: str
    initial_balance: Decimal
    current_balance: Decimal
    pnl_total: Decimal
    leverage_max: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperPositionRead(BaseModel):
    """Response model for open paper position."""

    id: UUID
    paper_account_id: UUID
    symbol: str
    side: Literal["LONG", "SHORT"]
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    leverage_used: int
    margin_required: Decimal
    unrealized_pnl: Decimal
    opened_at: datetime

    model_config = {"from_attributes": True}


class TakeProfitLevel(BaseModel):
    """Take-profit level definition."""

    level: int = Field(..., ge=1, le=5, description="TP level 1-5")
    price: Decimal = Field(..., gt=0, decimal_places=8)
    quantity: Decimal = Field(..., gt=0, decimal_places=8)


class PaperOrderCreate(BaseModel):
    """Input model for creating a paper order."""

    signal_id: UUID | None = None
    symbol: str = Field(..., min_length=2, max_length=20)
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    quantity: Decimal = Field(..., gt=0, decimal_places=8)
    entry_price: Decimal = Field(..., gt=0, decimal_places=8)
    stop_loss: Decimal | None = Field(None, gt=0, decimal_places=8)
    take_profit: list[TakeProfitLevel] = Field(default_factory=list, max_length=5)
    leverage: int = Field(default=1, ge=1, le=10)

    @field_validator("quantity", "entry_price")
    @classmethod
    def validate_positive_decimals(cls, v: Decimal) -> Decimal:
        """Validate positive decimal values."""
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        if not v.replace("USDT", "").replace("BUSD", "").isalpha():
            raise ValueError("Symbol must be alphanumeric")
        return v.upper()


class PaperOrderRead(BaseModel):
    """Response model for paper order."""

    id: UUID
    paper_account_id: UUID
    signal_id: UUID | None
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    quantity: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: list[TakeProfitLevel]
    leverage: int
    status: Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"]
    rejection_reason: str | None
    created_at: datetime
    filled_at: datetime | None

    model_config = {"from_attributes": True}


class PaperTradeRead(BaseModel):
    """Response model for paper trade (open or closed)."""

    id: UUID
    paper_account_id: UUID
    order_id: UUID
    symbol: str
    side: Literal["LONG", "SHORT"]
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal | None
    leverage: int
    pnl: Decimal | None
    pnl_percent: Decimal | None
    fees_paid: Decimal
    status: Literal["OPEN", "CLOSED", "LIQUIDATED"]
    exit_reason: str | None
    opened_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class PerformanceMetrics(BaseModel):
    """Aggregate performance metrics for a paper account."""

    account_id: UUID
    total_trades: int
    open_trades: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    total_pnl: Decimal
    total_pnl_percent: Decimal
    avg_win: Decimal | None
    avg_loss: Decimal | None
    profit_factor: Decimal | None
    sharpe_ratio: Decimal | None
    max_drawdown: Decimal | None
