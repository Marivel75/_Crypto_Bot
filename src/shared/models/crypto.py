"""Shared Pydantic models for crypto market data.

Used by ALL teams. Do not modify without notifying other teams.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OHLCVRecord(BaseModel):
    """OHLCV (candlestick) data for a single crypto on one timeframe."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., description="Trading pair, e.g. BTCUSDT")
    price_open: Decimal
    price_high: Decimal
    price_low: Decimal
    price_close: Decimal
    volume_24h: Decimal
    market_cap: Decimal | None = None
    timestamp: datetime
    source: str = Field(..., description="Data source, e.g. binance, coingecko")
    timeframe: str = Field(..., description="Candle interval, e.g. 1m, 5m, 1h, 4h, 1D")

    @model_validator(mode="after")
    def validate_ohlcv_constraints(self) -> OHLCVRecord:
        if self.price_high < self.price_low:
            msg = f"price_high ({self.price_high}) must be >= price_low ({self.price_low})"
            raise ValueError(msg)
        if self.volume_24h < 0:
            msg = f"volume_24h must be >= 0, got {self.volume_24h}"
            raise ValueError(msg)
        return self


class IndicatorRecord(BaseModel):
    """Computed technical indicators for a crypto on a given timeframe."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    timeframe: str
    timestamp: datetime
    # RSI value in range [0, 100]
    rsi: Decimal | None = None
    bollinger_upper: Decimal | None = None
    bollinger_middle: Decimal | None = None
    bollinger_lower: Decimal | None = None
    # Relative position of the price within the Bollinger bands (-1 to 1)
    price_vs_bollinger: Decimal | None = Field(None, description="Price position within Bollinger bands (-1 to 1)")
    # Detected harmonic pattern name, e.g. Gartley, Butterfly
    harmonic_pattern: str | None = Field(None, description="Harmonic pattern name, e.g. Gartley, Butterfly")
    trend_slope: Decimal | None = None
    # Trend classification, e.g. stable, aggressive
    trend_type: str | None = Field(None, description="Trend classification, e.g. stable, aggressive")
    metadata: dict = Field(default_factory=dict)


class NewsArticle(BaseModel):
    """Scraped or API-fetched news article."""

    model_config = ConfigDict(frozen=True)

    title: str
    content: str | None = None
    source: str
    url: str
    published_at: datetime | None = None
    # Sentiment score in range [-1 (negative) to 1 (positive)]
    sentiment_score: Decimal | None = Field(None, description="Sentiment score from -1 (negative) to 1 (positive)")
    keywords: list[str] = Field(default_factory=list)
    reliability_score: Decimal | None = None
