"""Bitcoin mempool.space data collector.

Fetches Bitcoin network statistics and mempool metrics from mempool.space API.
Free tier: ~1 request/second soft limit.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.models.onchain import MempoolRecord

logger = logging.getLogger(__name__)

MEMPOOL_BASE_URL = "https://mempool.space/api"
MEMPOOL_TIMEOUT = httpx.Timeout(timeout=30.0, connect=10.0)


class MempoolCollector:
    """Collects Bitcoin on-chain data from mempool.space."""

    def __init__(self) -> None:
        """Initialize collector with async HTTP client."""
        self.client = httpx.AsyncClient(timeout=MEMPOOL_TIMEOUT, http2=True)
        self.base_url = MEMPOOL_BASE_URL

    async def __aenter__(self) -> MempoolCollector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit — close client."""
        await self.client.aclose()

    async def fetch_latest_block(self) -> MempoolRecord:
        """Fetch latest block info and mempool stats.

        Returns:
            MempoolRecord with current block height, mempool transaction count,
            and fee rate estimates.

        Raises:
            RateLimitError: If API returns 429
            ExternalAPIError: If API fails or returns invalid data
        """
        try:
            # Fetch mempool stats
            mempool_response = await self._fetch_with_retry(f"{self.base_url}/mempool")
            mempool_data = mempool_response.json()

            # Fetch latest block
            blocks_response = await self._fetch_with_retry(f"{self.base_url}/blocks/tip/height")
            block_height = int(blocks_response.text)

            # Parse fee rates (in sat/vB)
            vsize_fee = mempool_data.get("vsize_fee", {})
            total_fee = mempool_data.get("total_fee_rate", 1.0)

            return MempoolRecord(
                symbol="BTC",
                source="mempool",
                unconfirmed_count=mempool_data.get("count", 0),
                total_fee_rate=Decimal(str(total_fee)),
                min_fee_rate=Decimal(str(vsize_fee.get("slow", 1.0))),
                max_fee_rate=Decimal(str(vsize_fee.get("fast", 100.0))),
                block_height=block_height,
                block_timestamp=datetime.utcnow(),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                msg = f"Mempool API rate limit (429): {e.response.text}"
                raise RateLimitError(msg) from e
            msg = f"Mempool API HTTP error {e.response.status_code}: {e.response.text}"
            raise ExternalAPIError(msg) from e
        except (httpx.RequestError, ValueError, KeyError) as e:
            msg = f"Mempool API error: {type(e).__name__}: {e}"
            raise ExternalAPIError(msg) from e

    async def fetch_mempool_stats(self) -> dict[str, Any]:
        """Fetch raw mempool stats for debugging.

        Returns:
            Raw JSON response from /api/mempool
        """
        try:
            response = await self._fetch_with_retry(f"{self.base_url}/mempool")
            return response.json()  # type: ignore
        except Exception as e:
            msg = f"Failed to fetch mempool stats: {e}"
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
                    f"Mempool fetch failed (attempt {attempt}/{max_retries}): "
                    f"{type(last_error).__name__}. Retrying in {wait_seconds}s..."
                )
                await asyncio.sleep(wait_seconds)

        msg = f"Failed to fetch {url} after {max_retries} attempts: {type(last_error).__name__}: {last_error}"
        raise ExternalAPIError(msg) from last_error
