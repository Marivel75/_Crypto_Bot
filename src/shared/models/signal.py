"""Shared Pydantic models for trading signals.

Used by ALL teams. Do not modify without notifying other teams.
Signals are strictly informational — no automated trade execution.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TradingSignal(BaseModel):
    """Informational trading signal (no automated execution)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    # Direction of the signal: BUY, SELL, or HOLD
    signal_type: Literal["BUY", "SELL", "HOLD"] = Field(..., description="BUY, SELL, or HOLD")
    # Only signals with confidence >= 0.6 are emitted
    confidence_score: Decimal = Field(..., ge=0, le=1)
    timeframe_primary: str = Field(..., description="Primary timeframe for this signal")
    # Indicator state per timeframe, e.g. {"1h": {"rsi": 68}, "4h": {"rsi": 70}}
    timeframes_aligned: dict = Field(
        default_factory=dict,
        description='Indicator state per timeframe, e.g. {"1h": {"rsi": 68}, "4h": {"rsi": 70}}',
    )
    # Rule names that triggered this signal, e.g. ["rsi_overbought_multi_tf"]
    rules_triggered: list[str] = Field(
        default_factory=list,
        description='Rule names that triggered this signal, e.g. ["rsi_overbought_multi_tf"]',
    )
    # Suggested leverage; must satisfy the 2x margin safety rule
    leverage_suggested: int | None = Field(None, ge=1, le=20, description="Suggested leverage (5, 10, or 20)")
    # Minimum margin required (2x the notional position)
    margin_safety: Decimal | None = Field(None, description="Minimum margin safety factor (2x position)")
    # Estimated total fees: maker + taker + funding rate
    fees_estimated: Decimal | None = Field(None, description="Estimated fees (maker + taker + funding)")
    # Model or rule-set version that produced this signal, e.g. rules_v1, xgboost_v2
    model_version: str = Field(..., description="Model or rule-set version, e.g. rules_v1, xgboost_v2")
    created_at: datetime | None = None


class SignalOutcome(BaseModel):
    """Post-hoc evaluation of a trading signal."""

    model_config = ConfigDict(frozen=True)

    signal_id: str
    price_at_signal: Decimal
    price_after_1h: Decimal | None = None
    price_after_4h: Decimal | None = None
    price_after_1d: Decimal | None = None
    # Simulated profit/loss if the signal had been followed
    pnl_simulated: Decimal | None = None
    # True if the predicted direction matched actual price movement
    was_correct: bool | None = None
    evaluated_at: datetime
