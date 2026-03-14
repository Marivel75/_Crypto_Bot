"""Shared configuration — reads environment variables via pydantic-settings.

Used by ALL teams. Import the ``settings`` singleton rather than
instantiating ``Settings`` directly.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables / .env file."""

    # ---------------------------------------------------------------------------
    # Database
    # ---------------------------------------------------------------------------
    database_url: str = "postgresql://cryptobot:password@timescaledb:5432/cryptobot"
    postgres_db: str = "cryptobot"
    postgres_user: str = "cryptobot"
    postgres_password: str = "password"  # noqa: S105

    # ---------------------------------------------------------------------------
    # MinIO object storage
    # ---------------------------------------------------------------------------
    minio_endpoint: str = "http://minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"  # noqa: S105

    # ---------------------------------------------------------------------------
    # FastAPI / JWT
    # ---------------------------------------------------------------------------
    api_secret_key: str = "dev-secret-key"  # noqa: S105
    api_host: str = "0.0.0.0"  # noqa: S104
    api_port: int = 8000
    api_url: str = "http://api:8000"

    # ---------------------------------------------------------------------------
    # External API keys (empty = use public / unauthenticated endpoints)
    # ---------------------------------------------------------------------------
    coingecko_api_key: str = ""

    # LLM providers — set at least one to enable the chat assistant
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    use_claude_cli: bool = True  # Use `claude` CLI (Max subscription) as primary LLM

    # ---------------------------------------------------------------------------
    # MLflow experiment tracking
    # ---------------------------------------------------------------------------
    mlflow_tracking_uri: str = "http://mlflow:5000"

    # ---------------------------------------------------------------------------
    # Tracked symbols (top symbols by market cap, modifiable via .env)
    # ---------------------------------------------------------------------------
    tracked_symbols: list[str] = [
        "BTC",
        "ETH",
        "USDT",
        "USDC",
        "BNB",
        "XRP",
        "SOL",
        "ADA",
        "AVAX",
        "DOT",
        "DOGE",
        "TRX",
        "ATOM",
    ]

    # ---------------------------------------------------------------------------
    # Supported OHLCV timeframes
    # ---------------------------------------------------------------------------
    timeframes: list[str] = ["1m", "5m", "1h", "2h", "3h", "4h", "1D", "1W", "1M"]

    # ---------------------------------------------------------------------------
    # CORS — allowed origins for the Streamlit frontend
    # ---------------------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:8501"]

    # ---------------------------------------------------------------------------
    # Logging
    # ---------------------------------------------------------------------------
    log_level: str = "INFO"

    # ---------------------------------------------------------------------------
    # JWT token lifetime
    # ---------------------------------------------------------------------------
    jwt_expiration_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
