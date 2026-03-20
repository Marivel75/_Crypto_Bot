"""Ethereum gas tracker data collector via Etherscan API.

Fetches Ethereum gas prices and blockchain stats from Etherscan.
Requires free API key from https://etherscan.io/apis
Rate limit: 5 requests/second, 100,000 requests/day
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.models.onchain import EtherscanGasStats

logger = logging.getLogger(__name__)

ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"
ETHERSCAN_TIMEOUT = httpx.Timeout(timeout=30.0, connect=10.0)


class EtherscanCollector:
    """Collects Ethereum gas and blockchain data from Etherscan API."""

    def __init__(self, api_key: str) -> None:
        """Initialize collector.

        Args:
            api_key: Etherscan API key (free tier from etherscan.io)
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=ETHERSCAN_TIMEOUT, http2=True)
        self.base_url = ETHERSCAN_BASE_URL

    async def __aenter__(self) -> EtherscanCollector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit — close client."""
        await self.client.aclose()

    async def fetch_gas_stats(self) -> EtherscanGasStats:
        """Fetch current Ethereum gas prices and block info.

        Returns:
            EtherscanGasStats with gas prices and block data.

        Raises:
            RateLimitError: If API returns 429
            ExternalAPIError: If API fails or returns invalid data
        """
        try:
            # Fetch gas prices
            gas_response = await self._fetch_with_retry(
                self.base_url,
                params={
                    "module": "gastracker",
                    "action": "gasprices",
                    "apikey": self.api_key,
                },
            )
            gas_data = gas_response.json()

            if gas_data.get("status") != "1":
                msg = f"Etherscan error: {gas_data.get('message', 'Unknown error')}"
                raise ExternalAPIError(msg)

            result = gas_data.get("result", {})

            # Fetch ETH price
            price_response = await self._fetch_with_retry(
                self.base_url,
                params={
                    "module": "stats",
                    "action": "ethprice",
                    "apikey": self.api_key,
                },
            )
            price_data = price_response.json()
            eth_price = float(price_data.get("result", {}).get("ethusd", "0"))

            # Fetch latest block
            block_response = await self._fetch_with_retry(
                self.base_url,
                params={
                    "module": "proxy",
                    "action": "eth_blockNumber",
                    "apikey": self.api_key,
                },
            )
            block_data = block_response.json()
            block_number = int(block_data.get("result", "0"), 16)

            return EtherscanGasStats(
                symbol="ETH",
                source="etherscan",
                safe_gas_price_gwei=Decimal(str(result.get("SafeGasPrice", 0))),
                standard_gas_price_gwei=Decimal(str(result.get("StandardGasPrice", 0))),
                fast_gas_price_gwei=Decimal(str(result.get("FastGasPrice", 0))),
                base_fee_gwei=Decimal(str(result.get("suggestBaseFee", 0))),
                eth_price_usd=Decimal(str(eth_price)),
                block_number=block_number,
                block_timestamp=datetime.utcnow(),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                msg = f"Etherscan API rate limit (429): {e.response.text}"
                raise RateLimitError(msg) from e
            msg = f"Etherscan API HTTP error {e.response.status_code}: {e.response.text}"
            raise ExternalAPIError(msg) from e
        except (httpx.RequestError, ValueError, KeyError) as e:
            msg = f"Etherscan API error: {type(e).__name__}: {e}"
            raise ExternalAPIError(msg) from e

    async def _fetch_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> httpx.Response:
        """Fetch URL with exponential backoff retry.

        Args:
            url: Base URL to fetch
            params: Query parameters
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff multiplier

        Returns:
            httpx.Response object

        Raises:
            RateLimitError: On HTTP 429
            ExternalAPIError: On other HTTP errors or connection failures
        """
        attempt = 0
        last_error: httpx.HTTPStatusError | httpx.TimeoutException | httpx.NetworkError | None = None

        while attempt < max_retries:
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After", "60")
                    msg = f"Rate limited. Retry after {retry_after}s. URL: {url}"
                    raise RateLimitError(msg) from e
                last_error = e
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e

            attempt += 1
            if attempt < max_retries:
                wait_seconds = backoff_factor**attempt
                logger.warning(
                    f"Etherscan fetch failed (attempt {attempt}/{max_retries}): "
                    f"{type(last_error).__name__}. Retrying in {wait_seconds}s..."
                )
                await asyncio.sleep(wait_seconds)

        msg = f"Failed to fetch {url} after {max_retries} attempts: {type(last_error).__name__}: {last_error}"
        raise ExternalAPIError(msg) from last_error
