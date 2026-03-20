"""Bitcoin blockchain.com data collector.

Fetches Bitcoin network statistics from blockchain.com API.
Free tier: ~10 requests/second soft limit.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.models.onchain import BlockchainBTCStats

logger = logging.getLogger(__name__)

BLOCKCHAIN_BASE_URL = "https://blockchain.info/api"
BLOCKCHAIN_TIMEOUT = httpx.Timeout(timeout=30.0, connect=10.0)


class BlockchainCollector:
    """Collects Bitcoin blockchain data from blockchain.com."""

    def __init__(self) -> None:
        """Initialize collector with async HTTP client."""
        self.client = httpx.AsyncClient(timeout=BLOCKCHAIN_TIMEOUT, http2=True)
        self.base_url = BLOCKCHAIN_BASE_URL

    async def __aenter__(self) -> BlockchainCollector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit — close client."""
        await self.client.aclose()

    async def fetch_blockchain_stats(self) -> BlockchainBTCStats:
        """Fetch current blockchain statistics.

        Returns:
            BlockchainBTCStats with network metrics, transaction counts, fee estimates.

        Raises:
            RateLimitError: If API returns 429
            ExternalAPIError: If API fails or returns invalid data
        """
        try:
            # Fetch stats
            stats_response = await self._fetch_with_retry(f"{self.base_url}/charts/total-bitcoins?format=json")
            stats_data = stats_response.json()

            # Get latest data point
            data_points = stats_data.get("values", [])
            if not data_points:
                msg = "No data points returned from blockchain.info"
                raise ExternalAPIError(msg)

            latest = data_points[-1]

            # Fetch fee estimates
            fees_response = await self._fetch_with_retry(f"{self.base_url}/mempool?format=json")
            fees_data = fees_response.json()

            return BlockchainBTCStats(
                symbol="BTC",
                source="blockchain.com",
                hashrate_tph=Decimal(str(float(latest.get("x", 0)) / (10**12))),
                difficulty=Decimal(str(latest.get("y", 0))),
                total_btc_supply=Decimal(str(latest.get("z", 0))),
                avg_transaction_size_bytes=fees_data.get("tx_size", 250),
                mempool_transactions=fees_data.get("unconfirmed_count", 0),
                confirmed_transactions_24h=int(fees_data.get("n_tx_24h", 0)),
                fee_estimate_fast_sat=int(fees_data.get("fast", 10)),
                fee_estimate_standard_sat=int(fees_data.get("standard", 5)),
                timestamp=datetime.utcnow(),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                msg = f"Blockchain.info API rate limit (429): {e.response.text}"
                raise RateLimitError(msg) from e
            msg = f"Blockchain.info API HTTP error {e.response.status_code}: {e.response.text}"
            raise ExternalAPIError(msg) from e
        except (httpx.RequestError, ValueError, KeyError) as e:
            msg = f"Blockchain.info API error: {type(e).__name__}: {e}"
            raise ExternalAPIError(msg) from e

    async def fetch_hashrate(self) -> float:
        """Fetch Bitcoin network hashrate in TH/s.

        Returns:
            Hashrate in terahashes per second.
        """
        try:
            response = await self._fetch_with_retry(f"{self.base_url}/q/hashrate")
            return float(response.text) / (10**12)  # Convert H/s to TH/s
        except Exception as e:
            msg = f"Failed to fetch hashrate: {e}"
            raise ExternalAPIError(msg) from e

    async def fetch_difficulty(self) -> float:
        """Fetch Bitcoin network difficulty.

        Returns:
            Current difficulty value.
        """
        try:
            response = await self._fetch_with_retry(f"{self.base_url}/q/difficulty")
            return float(response.text)
        except Exception as e:
            msg = f"Failed to fetch difficulty: {e}"
            raise ExternalAPIError(msg) from e

    async def _fetch_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> httpx.Response:
        """Fetch URL with exponential backoff retry.

        Args:
            url: Full URL to fetch
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
                response = await self.client.get(url)
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
                    f"Blockchain.com fetch failed (attempt {attempt}/{max_retries}): "
                    f"{type(last_error).__name__}. Retrying in {wait_seconds}s..."
                )
                await asyncio.sleep(wait_seconds)

        msg = f"Failed to fetch {url} after {max_retries} attempts: {type(last_error).__name__}: {last_error}"
        raise ExternalAPIError(msg) from last_error
