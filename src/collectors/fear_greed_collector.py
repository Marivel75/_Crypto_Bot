"""Collecteur synchrone du Fear & Greed Index (alternative.me).

Interroge l'API alternative.me pour récupérer l'indice de sentiment du marché
crypto (0 = peur extrême, 100 = avidité extrême).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)

_URL = "https://api.alternative.me/fng/?limit=1"
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class FearGreedResult(TypedDict):
    value: int
    classification: str
    timestamp: datetime


class FearGreedCollector:
    """Synchronous collector for the Alternative.me Fear & Greed Index."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={"Accept": "application/json"},
            timeout=_TIMEOUT,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> FearGreedCollector:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch(self) -> FearGreedResult:
        """Fetch the current Fear & Greed index from alternative.me.

        Returns:
            FearGreedResult with value (0–100), classification, and UTC timestamp.

        Raises:
            httpx.HTTPStatusError: on non-2xx response.
            ValueError: if the API payload is malformed.
        """
        logger.info("Fetching Alternative.me Fear & Greed Index")
        response = self._client.get(_URL)
        response.raise_for_status()
        result = self._parse(response.json())
        logger.info(
            "Fear & Greed: value=%d classification=%s",
            result["value"],
            result["classification"],
        )
        return result

    @staticmethod
    def _parse(payload: dict) -> FearGreedResult:
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError(f"Unexpected Fear & Greed response: {payload!r}")

        entry = data[0]
        raw_value = entry.get("value")
        raw_class = entry.get("value_classification")
        raw_ts = entry.get("timestamp")

        if raw_value is None or raw_class is None or raw_ts is None:
            raise ValueError(f"Missing fields in Fear & Greed entry: {entry!r}")

        try:
            value = int(str(raw_value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Cannot parse value '{raw_value}' as int") from exc

        try:
            timestamp = datetime.fromtimestamp(int(str(raw_ts)), tz=timezone.utc)
        except (ValueError, TypeError, OSError) as exc:
            raise ValueError(f"Cannot parse timestamp '{raw_ts}'") from exc

        return FearGreedResult(value=value, classification=str(raw_class), timestamp=timestamp)
