"""CoinGecko Demo API collector — fetches market data for tracked symbols."""

from __future__ import annotations

import logging

import httpx

from src.shared.config import settings
from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.coingecko.com/api/v3"
_MARKETS_ENDPOINT = "/coins/markets"

# CoinGecko uses lowercase coin IDs that differ from Binance pair symbols.
# This map translates our internal symbol (e.g. "BTC") to the CoinGecko coin ID.
_SYMBOL_TO_COINGECKO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "SOL": "solana",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "ATOM": "cosmos",
}


class CoinGeckoCollector:
    """Async collector for CoinGecko market data (Demo API, 30 req/min).

    Uses a shared httpx.AsyncClient. Call ``await collector.close()`` when
    finished, or use as an async context manager.
    """

    def __init__(self) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.coingecko_api_key:
            headers["x-cg-demo-key"] = settings.coingecko_api_key

        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=headers,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> CoinGeckoCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_market_data(self, symbols: list[str]) -> list[dict[str, object]]:
        """Fetch market data for a list of symbols from CoinGecko /coins/markets.

        Args:
            symbols: List of internal symbol names, e.g. ``["BTC", "ETH"]``.
                     Unknown symbols are silently skipped with a warning.

        Returns:
            List of raw market data dicts as returned by CoinGecko.
            Each dict contains keys such as ``id``, ``symbol``, ``current_price``,
            ``market_cap``, ``total_volume``, etc.

        Raises:
            RateLimitError: When CoinGecko returns HTTP 429.
            ExternalAPIError: On any other non-2xx response or network error.
        """
        coin_ids = self._resolve_coin_ids(symbols)
        if not coin_ids:
            logger.warning("No resolvable CoinGecko IDs for symbols: %s", symbols)
            return []

        logger.info(
            "Fetching CoinGecko market data: symbols=%s coin_ids=%s",
            symbols,
            coin_ids,
        )

        data: list[dict[str, object]] = await with_retry(
            lambda: self._get_markets(coin_ids),
            max_attempts=5,
            base_delay=2.0,  # CoinGecko rate limit is stricter (30 req/min)
            exceptions=(RateLimitError, ExternalAPIError, httpx.TransportError),
        )

        logger.info(
            "CoinGecko market data collected: symbols=%s records=%d",
            symbols,
            len(data),
        )
        return data

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_coin_ids(self, symbols: list[str]) -> list[str]:
        """Convert internal symbol names to CoinGecko coin IDs."""
        ids: list[str] = []
        for sym in symbols:
            coin_id = _SYMBOL_TO_COINGECKO_ID.get(sym.upper())
            if coin_id:
                ids.append(coin_id)
            else:
                logger.warning("No CoinGecko ID mapping found for symbol '%s', skipping.", sym)
        return ids

    async def _get_markets(self, coin_ids: list[str]) -> list[dict[str, object]]:
        """Execute the /coins/markets HTTP request."""
        try:
            response = await self._client.get(
                _MARKETS_ENDPOINT,
                params={
                    "vs_currency": "usd",
                    "ids": ",".join(coin_ids),
                    "order": "market_cap_desc",
                    "per_page": len(coin_ids),
                    "page": 1,
                    "sparkline": "false",
                },
            )
        except httpx.TransportError as exc:
            raise ExternalAPIError(f"Network error contacting CoinGecko: {exc}", detail=str(exc)) from exc

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            raise RateLimitError(
                f"CoinGecko rate limit exceeded (Retry-After: {retry_after})",
                detail={"retry_after": retry_after},
            )

        if response.status_code != 200:
            raise ExternalAPIError(
                f"CoinGecko API returned HTTP {response.status_code}",
                detail=response.text[:200],
            )

        try:
            result: list[dict[str, object]] = response.json()
        except ValueError as exc:
            raise ExternalAPIError(
                "CoinGecko API returned invalid JSON",
                detail=response.text[:200],
            ) from exc
        return result
