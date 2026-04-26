"""HTTP client for the Crypto Bot FastAPI backend.

All methods return parsed JSON (dict or list) on success, None on any error.
No JWT/auth — the backend is unauthenticated.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from frontend.config import frontend_settings

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


class APIClient:
    """Thin synchronous wrapper around httpx for the Crypto Bot API."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or frontend_settings.api_url).rstrip("/")

    # ------------------------------------------------------------------
    # Low-level helper
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET *path* and return the parsed JSON body, or None on error."""
        url = f"{self._base}{path}"
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                r = client.get(url, params=params)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            logger.warning("GET %s → HTTP %s", path, r.status_code)
            return None
        except httpx.RequestError as exc:
            logger.error("GET %s failed: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # OHLCV endpoints
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 200,
        exchange: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """GET /ohlcv — filtered by symbol/timeframe, ordered DESC by timestamp."""
        params: dict[str, Any] = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
        if exchange:
            params["exchange"] = exchange
        result = self.get("/ohlcv", params)
        if not isinstance(result, list):
            return None
        return result

    def fetch_symbols(self, exchange: str | None = None) -> list[dict[str, Any]] | None:
        """GET /ohlcv/symbols — list of available (symbol, exchange, timeframe, count)."""
        params = {"exchange": exchange} if exchange else None
        result = self.get("/ohlcv/symbols", params)
        return result if isinstance(result, list) else None

    def fetch_latest(self, timeframe: str = "1d") -> list[dict[str, Any]] | None:
        """GET /ohlcv/latest — most recent candle per symbol for the given timeframe."""
        result = self.get("/ohlcv/latest", {"timeframe": timeframe})
        return result if isinstance(result, list) else None

    # ------------------------------------------------------------------
    # Signals endpoint
    # ------------------------------------------------------------------

    def fetch_signals(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        exchange: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """GET /signals — OHLCV + computed technical indicators per candle.

        Returns None when the symbol is unknown (404) or on network error.
        Rows are ordered ASC by timestamp (oldest first) by the API.
        """
        params: dict[str, Any] = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
        if exchange:
            params["exchange"] = exchange
        result = self.get("/signals", params)
        if not isinstance(result, list):
            return None
        return result

    # ------------------------------------------------------------------
    # Market endpoints
    # ------------------------------------------------------------------

    def fetch_market_top(
        self, limit: int = 20, currency: str = "usd"
    ) -> dict[str, Any] | None:
        """GET /market/top — latest top-crypto snapshot with ranked list."""
        result = self.get("/market/top", {"limit": limit, "currency": currency})
        return result if isinstance(result, dict) else None

    def fetch_market_global(self) -> dict[str, Any] | None:
        """GET /market/global — global market cap, volume, dominance."""
        result = self.get("/market/global")
        return result if isinstance(result, dict) else None

    def fetch_ticker(
        self,
        symbol: str | None = None,
        exchange: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """GET /market/ticker — ticker snapshots, optionally filtered."""
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        if exchange:
            params["exchange"] = exchange
        result = self.get("/market/ticker", params or None)
        return result if isinstance(result, list) else None
