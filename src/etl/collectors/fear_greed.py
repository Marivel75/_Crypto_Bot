"""Alternative.me Fear & Greed Index collector."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict

import httpx

from src.shared.exceptions import ExternalAPIError
from src.shared.models.crypto import OHLCVRecord
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_URL = "https://api.alternative.me/fng/?limit=1"
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class FearGreedResult(TypedDict):
    """Typed dict returned by ``FearGreedCollector.fetch_fear_greed``."""

    value: int
    value_classification: str
    timestamp: datetime


class FearGreedCollector:
    """Async collector for the Alternative.me Fear & Greed Index.

    Uses a shared httpx.AsyncClient. Call ``await collector.close()``
    when finished, or use as an async context manager.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"Accept": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> FearGreedCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_fear_greed(self) -> FearGreedResult:
        """Fetch the latest Fear & Greed index value.

        Returns:
            A ``FearGreedResult`` dict with keys:
            - ``value``: int in range [0, 100]
            - ``value_classification``: e.g. ``"Extreme Fear"``, ``"Greed"``
            - ``timestamp``: timezone.utc-aware ``datetime``

        Raises:
            ExternalAPIError: On non-2xx HTTP response or network error.
            ValueError: If the API response is missing expected fields.
        """
        logger.info("Fetching Alternative.me Fear & Greed Index")

        result: FearGreedResult = await with_retry(
            self._get_fear_greed,
            max_attempts=3,
            base_delay=2.0,
            exceptions=(ExternalAPIError, httpx.TransportError, ValueError),
        )

        logger.info(
            "Fear & Greed collected: value=%d classification=%s timestamp=%s",
            result["value"],
            result["value_classification"],
            result["timestamp"].isoformat(),
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_fear_greed(self) -> FearGreedResult:
        """Execute the HTTP request and parse the response."""
        try:
            response = await self._client.get(_URL)
        except httpx.TransportError as exc:
            raise ExternalAPIError(f"Network error contacting Alternative.me: {exc}", detail=str(exc)) from exc

        if response.status_code != 200:
            raise ExternalAPIError(
                f"Alternative.me API returned HTTP {response.status_code}",
                detail=response.text[:200],
            )

        payload: dict[str, object] = response.json()
        return self._parse_response(payload)

    @staticmethod
    def _parse_response(payload: dict[str, object]) -> FearGreedResult:
        """Extract and validate fields from the raw API payload.

        Expected structure:
        {
            "data": [
                {
                    "value": "42",
                    "value_classification": "Fear",
                    "timestamp": "1700000000"
                }
            ]
        }
        """
        data_list = payload.get("data")
        if not isinstance(data_list, list) or not data_list:
            raise ValueError(f"Unexpected Alternative.me response structure: {payload!r}")

        entry: dict[str, object] = data_list[0]  # type: ignore[assignment]

        raw_value = entry.get("value")
        raw_classification = entry.get("value_classification")
        raw_timestamp = entry.get("timestamp")

        if raw_value is None or raw_classification is None or raw_timestamp is None:
            raise ValueError(f"Missing required fields in Fear & Greed entry: {entry!r}")

        try:
            value = int(str(raw_value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Cannot parse Fear & Greed value '{raw_value}' as int") from exc

        try:
            timestamp = datetime.fromtimestamp(int(str(raw_timestamp)), tz=timezone.utc)
        except (ValueError, TypeError, OSError) as exc:
            raise ValueError(f"Cannot parse Fear & Greed timestamp '{raw_timestamp}'") from exc

        return FearGreedResult(
            value=value,
            value_classification=str(raw_classification),
            timestamp=timestamp,
        )

    async def fetch_as_ohlcv(self) -> list[OHLCVRecord]:
        """Fetch Fear & Greed and return as pseudo-OHLCV records for storage.

        The index value (0-100) is stored in all price fields so it fits
        the existing crypto_prices table and query patterns.
        """
        result = await self.fetch_fear_greed()
        value = Decimal(str(result["value"]))
        return [
            OHLCVRecord(
                symbol="FEAR_GREED",
                price_open=value,
                price_high=value,
                price_low=value,
                price_close=value,
                volume_24h=Decimal("0"),
                market_cap=None,
                timestamp=result["timestamp"],
                source="alternative.me",
                timeframe="1D",
            )
        ]
