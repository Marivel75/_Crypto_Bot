"""API request/response schemas — Pydantic v2 models.

All request/response models for the FastAPI layer.
Internal business logic uses src.shared.models.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


# --- Envelope ---


class ErrorDetail(BaseModel):
    """Structured error information returned inside ``ApiResponse``."""

    code: str
    message: str


class PaginationMeta(BaseModel):
    """Pagination metadata attached to list responses."""

    total: int
    page: int
    limit: int


class ApiResponse(BaseModel, Generic[T]):
    """Consistent response envelope for all API endpoints.

    Either ``data`` or ``error`` is populated, never both.
    ``meta`` is included only for paginated list responses.
    """

    data: T | None = None
    error: ErrorDetail | None = None
    meta: PaginationMeta | None = None


# --- Auth ---


class RegisterRequest(BaseModel):
    """Request body for POST /auth/register."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr = Field(..., min_length=1, max_length=254, description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128)
    persona_type: Literal["trader", "journalist", "investor"] = Field(
        ..., description="trader, journalist, or investor"
    )

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            msg = "Password must contain at least one uppercase letter"
            raise ValueError(msg)
        if not re.search(r"\d", v):
            msg = "Password must contain at least one digit"
            raise ValueError(msg)
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            msg = "Password must contain at least one special character"
            raise ValueError(msg)
        return v


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr = Field(..., min_length=1, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)


class LoginResponse(BaseModel):
    """JWT token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105


class UserResponse(BaseModel):
    """Public user profile returned by the API (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    persona_type: str
    preferences: dict = Field(default_factory=dict)
    created_at: datetime


# --- Crypto ---


class CryptoListItem(BaseModel):
    """A single tracked cryptocurrency symbol."""

    symbol: str
    name: str | None = None


class OHLCVResponse(BaseModel):
    """OHLCV candlestick data for a symbol at a given timeframe."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    timeframe: str
    timestamp: datetime
    price_open: float
    price_high: float
    price_low: float
    price_close: float
    volume_24h: float
    market_cap: float | None = None
    source: str


class IndicatorResponse(BaseModel):
    """Computed technical indicators for a symbol at a given timeframe."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    timeframe: str
    timestamp: datetime
    rsi: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    # Relative price position within the Bollinger bands
    price_vs_bollinger: float | None = None
    harmonic_pattern: str | None = None
    trend_slope: float | None = None
    trend_type: str | None = None


class LatestResponse(BaseModel):
    """Latest OHLCV and indicator snapshot for a symbol."""

    symbol: str
    ohlcv: OHLCVResponse | None = None
    indicators: IndicatorResponse | None = None


class MarketOverviewResponse(BaseModel):
    """Aggregated market-wide overview data."""

    total_symbols: int
    total_market_cap: float | None = None
    btc_dominance: float | None = None
    # Fear & Greed Index value (0–100)
    fear_greed: int | None = None
    top_gainers: list[dict] = Field(default_factory=list)
    top_losers: list[dict] = Field(default_factory=list)
    heatmap: list[dict] = Field(default_factory=list)


# --- Signals ---


class SignalResponse(BaseModel):
    """Trading signal returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    signal_type: str
    confidence_score: float
    timeframe_primary: str
    timeframes_aligned: dict = Field(default_factory=dict)
    rules_triggered: list = Field(default_factory=list)
    leverage_suggested: int | None = None
    margin_safety: float | None = None
    fees_estimated: float | None = None
    model_version: str
    created_at: datetime


class SignalDetailResponse(BaseModel):
    """Trading signal with its post-hoc outcome, if evaluated."""

    signal: SignalResponse
    outcome: SignalOutcomeResponse | None = None


class SignalOutcomeResponse(BaseModel):
    """Post-hoc evaluation of a trading signal's accuracy."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    signal_id: UUID
    price_at_signal: float | None = None
    price_after_1h: float | None = None
    price_after_4h: float | None = None
    price_after_1d: float | None = None
    pnl_simulated: float | None = None
    was_correct: bool | None = None
    evaluated_at: datetime


class PerformanceResponse(BaseModel):
    """Aggregate signal performance statistics."""

    total_signals: int
    evaluated_signals: int
    correct_signals: int
    # Percentage of correct signals out of evaluated; None if no evaluated signals
    win_rate: float | None = None
    total_pnl: float | None = None


# --- News ---


class NewsResponse(BaseModel):
    """News article returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str | None = None
    source: str
    url: str
    published_at: datetime | None = None
    # Sentiment score in [-1, 1]: negative → positive
    sentiment_score: float | None = None
    keywords: list = Field(default_factory=list)
    reliability_score: float | None = None


class NewsSentimentResponse(BaseModel):
    """Aggregate sentiment stats for a source or symbol."""

    # Represents the source name when returned from the sentiment endpoint
    symbol: str
    sentiment_score: float | None = None
    article_count: int


# --- Portfolio ---


class PortfolioEntryResponse(BaseModel):
    """A single portfolio position returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    symbol: str
    quantity: float
    entry_price: float
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class PortfolioCreateRequest(BaseModel):
    """Request body for adding a new portfolio position."""

    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    notes: str | None = Field(None, max_length=1000)

    @field_validator("symbol")
    @classmethod
    def symbol_to_upper(cls, v: str) -> str:
        return v.upper()


class PortfolioUpdateRequest(BaseModel):
    """Request body for partially updating a portfolio position.

    All fields are optional; only non-None values are applied.
    """

    quantity: float | None = Field(None, gt=0)
    entry_price: float | None = Field(None, gt=0)
    notes: str | None = None


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary with aggregated statistics."""

    total_entries: int
    total_value: float | None = None
    total_cost: float | None = None
    unrealized_pnl: float | None = None
    allocation: dict[str, float] = Field(default_factory=dict)


class PortfolioHistoryEntry(BaseModel):
    """A single historical portfolio value snapshot."""

    timestamp: datetime
    total_value: float
    entry_count: int


class PortfolioHistoryResponse(BaseModel):
    """Portfolio value history over time."""

    symbol: str | None = None
    history: list[PortfolioHistoryEntry] = Field(default_factory=list)


# --- Watchlist ---


class WatchlistEntryResponse(BaseModel):
    """A single watchlist entry returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    symbol: str
    added_at: datetime


class WatchlistAddRequest(BaseModel):
    """Request body for adding a symbol to the watchlist."""

    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z0-9]+$")

    @field_validator("symbol")
    @classmethod
    def symbol_to_upper(cls, v: str) -> str:
        return v.upper()


class WatchlistPriceResponse(BaseModel):
    """Current price snapshot for a watchlist symbol."""

    symbol: str
    current_price: float | None = None
    timestamp: datetime | None = None


# --- Chat ---


class ChatRequest(BaseModel):
    """Request body for the chat assistant endpoint."""

    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """LLM reply with an optional financial disclaimer."""

    reply: str
    # Populated when the message contains finance-related keywords
    disclaimer: str | None = None


# --- System ---


class HealthResponse(BaseModel):
    """Application health status returned by GET /health."""

    # "ok" or "degraded"
    status: str
    # "ok" or "error"
    database: str
    timestamp: datetime


class SourceStatusResponse(BaseModel):
    """Last ingestion timestamp and record count for a data source/symbol pair."""

    source: str
    symbol: str | None = None
    last_ingestion: datetime | None = None
    record_count: int = 0


class MetricsResponse(BaseModel):
    """Prometheus-style application metrics."""

    requests_total: int = 0
    requests_success: int = 0
    requests_error: int = 0
    request_latency_ms: float = 0.0
    database_connections: int = 0
