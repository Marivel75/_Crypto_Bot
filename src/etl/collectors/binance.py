"""Binance REST collector — fetches OHLCV kline data via the public API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.models.crypto import OHLCVRecord
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.binance.com"
_KLINES_ENDPOINT = "/api/v3/klines"

# Map internal timeframe labels to Binance interval strings.
_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "1h": "1h",
    "2h": "2h",
    "3h": "3h",
    "4h": "4h",
    "1D": "1d",
    "1W": "1w",
    "1M": "1M",
}

# Kline response column indices
_IDX_OPEN_TIME = 0
_IDX_OPEN = 1
_IDX_HIGH = 2
_IDX_LOW = 3
_IDX_CLOSE = 4
_IDX_VOLUME = 5


class BinanceCollector:
    """Async collector for Binance public OHLCV kline data.

    Uses a shared httpx.AsyncClient with connection pooling. Call
    ``await collector.close()`` when the collector is no longer needed, or
    use it as an async context manager.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> BinanceCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[OHLCVRecord]:
        """Fetch OHLCV klines from Binance for a single symbol/timeframe.

        Args:
            symbol: Binance trading pair, e.g. ``"BTCUSDT"``.
            timeframe: Internal timeframe label, e.g. ``"1h"``, ``"4h"``, ``"1D"``.
            limit: Number of candles to retrieve (max 1000 per Binance docs).

        Returns:
            List of validated ``OHLCVRecord`` instances ordered oldest-first.

        Raises:
            RateLimitError: When Binance returns HTTP 429.
            ExternalAPIError: On any other non-2xx response or network error.
        """
        interval = _TIMEFRAME_MAP.get(timeframe)
        if interval is None:
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Valid values: {list(_TIMEFRAME_MAP)}")

        logger.info(
            "Fetching Binance OHLCV: symbol=%s timeframe=%s limit=%d",
            symbol,
            timeframe,
            limit,
        )

        raw: list[list[object]] = await with_retry(
            lambda: self._get_klines(symbol, interval, limit),
            max_attempts=5,
            base_delay=1.0,
            exceptions=(RateLimitError, ExternalAPIError, httpx.TransportError),
        )

        records: list[OHLCVRecord] = []
        for i, row in enumerate(raw):
            try:
                records.append(self._parse_kline(row, symbol, timeframe))
            except (ValueError, TypeError, IndexError) as exc:
                logger.warning("Skipping malformed kline row %d for %s: %s", i, symbol, exc)

        logger.info(
            "Binance OHLCV collected: symbol=%s timeframe=%s records=%d",
            symbol,
            timeframe,
            len(records),
        )
        return records

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ) -> list[list[object]]:
        """Execute the HTTP request and return raw kline rows."""
        try:
            response = await self._client.get(
                _KLINES_ENDPOINT,
                params={"symbol": symbol, "interval": interval, "limit": limit},
            )
        except httpx.TransportError as exc:
            raise ExternalAPIError(f"Network error contacting Binance: {exc}", detail=str(exc)) from exc

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            raise RateLimitError(
                f"Binance rate limit exceeded (Retry-After: {retry_after})",
                detail={"retry_after": retry_after},
            )

        if response.status_code != 200:
            raise ExternalAPIError(
                f"Binance API returned HTTP {response.status_code}",
                detail=response.text[:200],
            )

        try:
            data: list[list[object]] = response.json()
        except ValueError as exc:
            raise ExternalAPIError(
                "Binance API returned invalid JSON",
                detail=response.text[:200],
            ) from exc
        return data

    @staticmethod
    def _parse_kline(row: list[object], symbol: str, timeframe: str) -> OHLCVRecord:
        """Map a single Binance kline array to an OHLCVRecord.

        Binance kline format:
        [open_time, open, high, low, close, volume, close_time, ...]
        All price/volume fields are returned as strings by Binance.
        """
        open_time_ms = int(row[_IDX_OPEN_TIME])  # type: ignore[call-overload]
        timestamp = datetime.fromtimestamp(open_time_ms / 1000, tz=UTC)

        return OHLCVRecord(
            symbol=symbol,
            price_open=Decimal(str(row[_IDX_OPEN])),
            price_high=Decimal(str(row[_IDX_HIGH])),
            price_low=Decimal(str(row[_IDX_LOW])),
            price_close=Decimal(str(row[_IDX_CLOSE])),
            volume_24h=Decimal(str(row[_IDX_VOLUME])),
            market_cap=None,
            timestamp=timestamp,
            source="binance",
            timeframe=timeframe,
        )
