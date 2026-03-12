"""Application-wide constants shared across all teams.

All values here are immutable. Do NOT mutate these collections at runtime.
"""

from __future__ import annotations

from decimal import Decimal

# ---------------------------------------------------------------------------
# Tracked cryptocurrency symbols (top 13 by market cap, Binance pairs)
# ---------------------------------------------------------------------------
TRACKED_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "USDCUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "DOGEUSDT",
    "TRXUSDT",
    "ATOMUSDT",
)

# ---------------------------------------------------------------------------
# Supported OHLCV timeframes
# ---------------------------------------------------------------------------
TIMEFRAMES: tuple[str, ...] = (
    "1m",
    "5m",
    "1h",
    "2h",
    "3h",
    "4h",
    "1D",
    "1W",
    "1M",
)

# ---------------------------------------------------------------------------
# External API rate limits (requests per minute)
# ---------------------------------------------------------------------------
BINANCE_RATE_LIMIT: int = 1200
COINGECKO_RATE_LIMIT: int = 30

# ---------------------------------------------------------------------------
# Signal rules
# ---------------------------------------------------------------------------
# Only emit signals whose confidence score meets or exceeds this threshold.
SIGNAL_CONFIDENCE_THRESHOLD: Decimal = Decimal("0.6")

SIGNAL_TYPES: tuple[str, ...] = ("BUY", "SELL", "HOLD")

# ---------------------------------------------------------------------------
# User persona types
# ---------------------------------------------------------------------------
PERSONA_TYPES: tuple[str, ...] = ("trader", "journalist", "investor")

# ---------------------------------------------------------------------------
# Pagination defaults
# ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ---------------------------------------------------------------------------
# External API URLs
# ---------------------------------------------------------------------------
BINANCE_BASE_URL: str = "https://api.binance.com"
COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
ALTERNATIVE_ME_FNG_URL: str = "https://api.alternative.me/fng/"

# ---------------------------------------------------------------------------
# MinIO bucket names
# ---------------------------------------------------------------------------
MINIO_BUCKET_RAW: str = "raw"
MINIO_BUCKET_DATASETS: str = "datasets"
MINIO_BUCKET_MODELS: str = "models"
MINIO_BUCKET_MLFLOW: str = "mlflow-artifacts"
MINIO_BUCKETS: tuple[str, ...] = (
    MINIO_BUCKET_RAW,
    MINIO_BUCKET_DATASETS,
    MINIO_BUCKET_MODELS,
    MINIO_BUCKET_MLFLOW,
)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------
RETRY_MAX_ATTEMPTS: int = 5
RETRY_BASE_DELAY: float = 1.0

# ---------------------------------------------------------------------------
# Indicator timeframes
# ---------------------------------------------------------------------------
RSI_BB_TIMEFRAMES: tuple[str, ...] = ("1h", "2h", "3h", "4h", "1D")
TREND_TIMEFRAMES: tuple[str, ...] = ("1D", "1W", "1M")

# ---------------------------------------------------------------------------
# Priority symbols (top 13 — collected every minute)
# ---------------------------------------------------------------------------
PRIORITY_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "DOGEUSDT",
    "TRXUSDT",
    "ATOMUSDT",
)

# ---------------------------------------------------------------------------
# News RSS feed URLs
# ---------------------------------------------------------------------------
NEWS_RSS_FEEDS: tuple[str, ...] = (
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://cryptonews.com/news/feed/",
)
