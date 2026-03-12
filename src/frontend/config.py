"""Frontend configuration — reads environment variables.

Does NOT import from src.shared.config to avoid pulling DB/MinIO secrets
into the frontend scope.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Streamlit frontend settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Backend API
    api_url: str = Field(default="http://api:8000", description="Backend API base URL")
    api_timeout: float = Field(default=10.0, description="HTTP request timeout in seconds")
    api_connect_timeout: float = Field(default=5.0, description="HTTP connect timeout in seconds")

    # Cache TTLs (seconds)
    cache_ttl_prices: int = Field(default=30, description="Cache TTL for OHLCV price data")
    cache_ttl_signals: int = Field(default=60, description="Cache TTL for trading signals")
    cache_ttl_news: int = Field(default=300, description="Cache TTL for news articles")
    cache_ttl_market: int = Field(default=300, description="Cache TTL for market overview data")

    # Tracked symbols — top coins by market cap, excluding stablecoins (USDT, USDC)
    tracked_symbols: list[str] = Field(
        default=[
            "BTC",
            "ETH",
            "BNB",
            "XRP",
            "SOL",
            "ADA",
            "AVAX",
            "DOT",
            "DOGE",
            "TRX",
            "ATOM",
        ],
        description="Tracked crypto symbols displayed in selectors",
    )

    # Timeframes — matches RSI multi-TF strategy (1h-4h) plus daily/weekly/monthly
    timeframes: list[str] = Field(
        default=["1h", "2h", "3h", "4h", "1D", "1W", "1M"],
        description="Timeframes available in chart selectors",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


frontend_settings = FrontendSettings()
