# Data Sources Quick-Start Implementation Guide

**Copy-paste-ready code snippets for Mempool, Etherscan, CryptoRank**

---

## 1. Mempool.space Collector (Bitcoin On-Chain)

**File**: `src/etl/collectors/mempool.py`

```python
"""Mempool.space collector — Bitcoin on-chain metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.mempool.space"
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class MempoolRecord:
    """Parsed Mempool response (use Pydantic model in production)."""
    def __init__(
        self,
        symbol: str,
        timestamp: datetime,
        block_height: int,
        tx_count: int,
        volume_btc: Decimal,
        fee_satoshi_per_vbyte: int,
    ) -> None:
        self.symbol = symbol
        self.timestamp = timestamp
        self.block_height = block_height
        self.tx_count = tx_count
        self.volume_btc = volume_btc
        self.fee_satoshi_per_vbyte = fee_satoshi_per_vbyte


class MempoolCollector:
    """Async collector for Mempool.space Bitcoin on-chain data."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> MempoolCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def fetch_latest_block(self) -> MempoolRecord:
        """Fetch latest block data."""
        logger.info("Fetching Mempool latest block")

        data = await with_retry(
            self._get_latest_block,
            max_attempts=5,
            base_delay=1.0,
            exceptions=(ExternalAPIError, httpx.TransportError),
        )

        timestamp = datetime.fromtimestamp(data["timestamp"], tz=UTC)
        return MempoolRecord(
            symbol="BTCUSD",
            timestamp=timestamp,
            block_height=data["height"],
            tx_count=data["tx_count"],
            volume_btc=Decimal(str(data.get("total_in", 0))),
            fee_satoshi_per_vbyte=data.get("avgFee", 0) // 4,  # vB estimate
        )

    async def fetch_mempool_stats(self) -> dict:
        """Fetch current mempool fee tiers."""
        logger.info("Fetching Mempool stats")

        response = await self._client.get("/api/v1/mempool")
        if response.status_code != 200:
            raise ExternalAPIError(
                f"Mempool API error: HTTP {response.status_code}",
                detail=response.text[:200],
            )

        return response.json()

    async def _get_latest_block(self) -> dict:
        """Execute HTTP request."""
        try:
            response = await self._client.get("/api/v1/blocks/tip/height")
            height = response.json()
            block_resp = await self._client.get(f"/api/v1/blocks?start_index=0")
            blocks = block_resp.json()
            if blocks and len(blocks) > 0:
                return blocks[0]
            raise ExternalAPIError("No blocks returned from Mempool", detail="")
        except httpx.TransportError as exc:
            raise ExternalAPIError(f"Network error: {exc}", detail=str(exc)) from exc
```

**Test**:
```python
# tests/unit/collectors/test_mempool.py
import pytest
from src.etl.collectors.mempool import MempoolCollector

@pytest.mark.asyncio
async def test_fetch_latest_block():
    async with MempoolCollector() as collector:
        record = await collector.fetch_latest_block()
        assert record.symbol == "BTCUSD"
        assert record.block_height > 0
        assert record.tx_count >= 0
```

---

## 2. Etherscan Collector (Ethereum Gas Tracker)

**File**: `src/etl/collectors/etherscan.py`

```python
"""Etherscan collector — Ethereum gas stats + price."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from src.shared.exceptions import ExternalAPIError, RateLimitError
from src.shared.config import settings
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.etherscan.io/api"
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class EtherscanGasStats:
    """Etherscan gas statistics."""
    def __init__(
        self,
        timestamp: datetime,
        safe_gas_gwei: Decimal,
        standard_gas_gwei: Decimal,
        fast_gas_gwei: Decimal,
        eth_usd_price: Decimal,
    ) -> None:
        self.timestamp = timestamp
        self.safe_gas_gwei = safe_gas_gwei
        self.standard_gas_gwei = standard_gas_gwei
        self.fast_gas_gwei = fast_gas_gwei
        self.eth_usd_price = eth_usd_price


class EtherscanCollector:
    """Async collector for Etherscan data."""

    def __init__(self, api_key: str = "") -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        self._api_key = api_key or settings.ETHERSCAN_API_KEY

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> EtherscanCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def fetch_gas_stats(self) -> EtherscanGasStats:
        """Fetch gas prices (Safe, Standard, Fast) + ETH/USD."""
        logger.info("Fetching Etherscan gas stats")

        data = await with_retry(
            self._get_gas_oracle,
            max_attempts=3,
            base_delay=2.0,
            exceptions=(ExternalAPIError, RateLimitError, httpx.TransportError),
        )

        return EtherscanGasStats(
            timestamp=datetime.now(UTC),
            safe_gas_gwei=Decimal(str(data["SafeGasPrice"])),
            standard_gas_gwei=Decimal(str(data["ProposeGasPrice"])),
            fast_gas_gwei=Decimal(str(data["FastGasPrice"])),
            eth_usd_price=Decimal(str(data.get("UsdPrice", 0))),
        )

    async def _get_gas_oracle(self) -> dict:
        """Execute gas tracker request."""
        try:
            response = await self._client.get(
                "",
                params={
                    "module": "gastracker",
                    "action": "gasoracle",
                    "apikey": self._api_key,
                },
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                raise RateLimitError(
                    f"Etherscan rate limit (Retry-After: {retry_after})",
                    detail={"retry_after": retry_after},
                )

            if response.status_code != 200:
                raise ExternalAPIError(
                    f"Etherscan error: HTTP {response.status_code}",
                    detail=response.text[:200],
                )

            payload = response.json()
            if payload.get("status") != "1":
                raise ExternalAPIError(
                    f"Etherscan API error: {payload.get('message', 'Unknown error')}",
                    detail=str(payload),
                )

            return payload["result"]

        except httpx.TransportError as exc:
            raise ExternalAPIError(f"Network error: {exc}", detail=str(exc)) from exc
```

**Config update** (`.env.example`):
```bash
ETHERSCAN_API_KEY=your_free_api_key_from_etherscan_io
```

**Test**:
```python
# tests/unit/collectors/test_etherscan.py
import pytest
from src.etl.collectors.etherscan import EtherscanCollector

@pytest.mark.asyncio
async def test_fetch_gas_stats():
    async with EtherscanCollector(api_key="test_key") as collector:
        stats = await collector.fetch_gas_stats()
        assert stats.safe_gas_gwei > 0
        assert stats.eth_usd_price > 0
```

---

## 3. CryptoRank Collector (Market Data + Rankings)

**File**: `src/etl/collectors/cryptorank.py`

```python
"""CryptoRank collector — Aggregated crypto market data."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict

import httpx

from src.shared.exceptions import ExternalAPIError
from src.shared.config import settings
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.cryptorank.io/v1"
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class CryptoRankCoinData(TypedDict, total=False):
    """CryptoRank coin response structure."""
    id: str
    symbol: str
    name: str
    rank: int
    price: float
    priceUSD: float
    marketCap: float | None
    volume24h: float | None
    change1h: float
    change24h: float
    change7d: float


class CryptoRankCollector:
    """Async collector for CryptoRank API (Sandbox free tier)."""

    def __init__(self, api_key: str = "") -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        self._api_key = api_key or settings.CRYPTORANK_API_KEY

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CryptoRankCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def fetch_all_coins(self, limit: int = 30) -> list[dict]:
        """Fetch top N coins by market cap with rankings."""
        logger.info(f"Fetching CryptoRank top {limit} coins")

        data = await with_retry(
            lambda: self._get_coins(limit),
            max_attempts=3,
            base_delay=2.0,
            exceptions=(ExternalAPIError, httpx.TransportError),
        )

        coins = []
        for coin_data in data:
            try:
                coin = {
                    "symbol": coin_data.get("symbol", "").upper(),
                    "rank": coin_data.get("rank", 0),
                    "price_usd": Decimal(str(coin_data.get("priceUSD", 0))),
                    "market_cap_usd": Decimal(str(coin_data.get("marketCap", 0))) if coin_data.get("marketCap") else None,
                    "volume_24h_usd": Decimal(str(coin_data.get("volume24h", 0))) if coin_data.get("volume24h") else None,
                    "change_1h_pct": Decimal(str(coin_data.get("change1h", 0))),
                    "change_24h_pct": Decimal(str(coin_data.get("change24h", 0))),
                    "change_7d_pct": Decimal(str(coin_data.get("change7d", 0))),
                    "timestamp": datetime.now(UTC),
                    "source": "cryptorank",
                }
                coins.append(coin)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed CryptoRank coin: {e}")
                continue

        logger.info(f"CryptoRank: fetched {len(coins)} coins")
        return coins

    async def _get_coins(self, limit: int) -> list[CryptoRankCoinData]:
        """Execute coins request."""
        try:
            response = await self._client.get(
                "/coins",
                params={
                    "limit": limit,
                    "sort": "rank",
                    "api_key": self._api_key,
                },
            )

            if response.status_code == 429:
                raise ExternalAPIError(
                    "CryptoRank rate limit exceeded (Sandbox: 100 req/min)",
                    detail=response.headers.get("Retry-After"),
                )

            if response.status_code != 200:
                raise ExternalAPIError(
                    f"CryptoRank API error: HTTP {response.status_code}",
                    detail=response.text[:200],
                )

            payload = response.json()
            if not isinstance(payload, list):
                raise ExternalAPIError(
                    "CryptoRank response not a list",
                    detail=str(payload)[:200],
                )

            return payload

        except httpx.TransportError as exc:
            raise ExternalAPIError(f"Network error: {exc}", detail=str(exc)) from exc
```

**Config update** (`.env.example`):
```bash
CRYPTORANK_API_KEY=your_sandbox_key_from_cryptorank_io
```

---

## 4. Integration with ETL Scheduler

**File**: `src/etl/scheduler.py` (add these jobs)

```python
"""APScheduler jobs for new data sources."""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.etl.collectors.mempool import MempoolCollector
from src.etl.collectors.etherscan import EtherscanCollector
from src.etl.collectors.cryptorank import CryptoRankCollector
from src.etl.database import get_db_session, insert_records

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def collect_mempool_data() -> None:
    """Collect Bitcoin on-chain metrics from Mempool.space."""
    try:
        async with MempoolCollector() as collector:
            record = await collector.fetch_latest_block()
            logger.info(f"Mempool: block {record.block_height}, {record.tx_count} txs")

            # Map to DB-storable format
            async with get_db_session() as session:
                # TODO: Implement insert_mempool_data(session, record)
                await session.commit()

    except Exception as e:
        logger.error(f"Mempool collection failed: {e}", exc_info=True)


async def collect_etherscan_gas() -> None:
    """Collect Ethereum gas prices from Etherscan."""
    try:
        async with EtherscanCollector() as collector:
            stats = await collector.fetch_gas_stats()
            logger.info(f"Etherscan: gas={stats.standard_gas_gwei} gwei, ETH=${stats.eth_usd_price}")

            # TODO: Implement insert_etherscan_stats(session, stats)

    except Exception as e:
        logger.error(f"Etherscan collection failed: {e}", exc_info=True)


async def collect_cryptorank_data() -> None:
    """Collect aggregated market data from CryptoRank."""
    try:
        async with CryptoRankCollector() as collector:
            coins = await collector.fetch_all_coins(limit=30)
            logger.info(f"CryptoRank: fetched {len(coins)} coins")

            # TODO: Implement insert_cryptorank_coins(session, coins)

    except Exception as e:
        logger.error(f"CryptoRank collection failed: {e}", exc_info=True)


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register new data source jobs."""
    global _scheduler
    _scheduler = scheduler

    # Bitcoin on-chain (every 10 min)
    scheduler.add_job(
        collect_mempool_data,
        "interval",
        minutes=10,
        name="collect_mempool_data",
        max_instances=1,
        misfire_grace_time=300,
    )

    # Ethereum gas (every 2 min, frequent market changes)
    scheduler.add_job(
        collect_etherscan_gas,
        "interval",
        minutes=2,
        name="collect_etherscan_gas",
        max_instances=1,
        misfire_grace_time=120,
    )

    # Market rankings (every 5 min, batch with CoinGecko)
    scheduler.add_job(
        collect_cryptorank_data,
        "interval",
        minutes=5,
        name="collect_cryptorank_data",
        max_instances=1,
        misfire_grace_time=300,
    )

    logger.info("New data source jobs registered")
```

---

## 5. Pydantic Models

**File**: `src/shared/models/onchain.py` (create new file)

```python
"""On-chain data models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class MempoolRecord(BaseModel):
    """Bitcoin on-chain metrics from Mempool.space."""
    symbol: str = "BTCUSD"
    timestamp: datetime
    block_height: int
    tx_count: int
    volume_btc: Decimal
    fee_satoshi_per_vbyte: int
    difficulty: Decimal | None = None
    source: str = "mempool.space"
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_onchain(self) -> MempoolRecord:
        if self.block_height < 0:
            raise ValueError("block_height must be >= 0")
        if self.tx_count < 0:
            raise ValueError("tx_count must be >= 0")
        return self


class EtherscanGasStats(BaseModel):
    """Ethereum gas statistics from Etherscan."""
    timestamp: datetime
    safe_gas_gwei: Decimal
    standard_gas_gwei: Decimal
    fast_gas_gwei: Decimal
    base_fee_wei: Decimal | None = None
    eth_usd_price: Decimal
    source: str = "etherscan"
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_gas(self) -> EtherscanGasStats:
        if self.safe_gas_gwei < 0 or self.safe_gas_gwei > self.standard_gas_gwei > self.fast_gas_gwei:
            raise ValueError("Gas price ordering must be: safe <= standard <= fast")
        return self


class CryptoRankCoin(BaseModel):
    """Market data from CryptoRank."""
    symbol: str
    rank: int
    price_usd: Decimal
    market_cap_usd: Decimal | None = None
    volume_24h_usd: Decimal | None = None
    change_1h_pct: Decimal
    change_24h_pct: Decimal
    change_7d_pct: Decimal
    timestamp: datetime
    source: str = "cryptorank"
    metadata: dict = Field(default_factory=dict)
```

---

## 6. Alembic Migration

**File**: `src/etl/migrations/versions/202603_add_onchain_sources.py` (create)

```python
"""Add on-chain data tables for Mempool, Etherscan, CryptoRank.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"


def upgrade() -> None:
    # Mempool data (Bitcoin on-chain)
    op.create_table(
        "mempool_data",
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("block_height", sa.Integer, nullable=False),
        sa.Column("tx_count", sa.Integer, nullable=False),
        sa.Column("volume_btc", sa.Numeric(20, 8), nullable=False),
        sa.Column("fee_satoshi_per_vbyte", sa.Integer, nullable=False),
        sa.Column("difficulty", sa.Numeric(30, 0), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timestamp"),
    )
    op.create_index("idx_mempool_block_height", "mempool_data", ["block_height"], postgresql_using="btree")

    # Etherscan gas stats (Ethereum on-chain)
    op.create_table(
        "etherscan_gas_stats",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, primary_key=True),
        sa.Column("safe_gas_gwei", sa.Numeric(10, 2), nullable=False),
        sa.Column("standard_gas_gwei", sa.Numeric(10, 2), nullable=False),
        sa.Column("fast_gas_gwei", sa.Numeric(10, 2), nullable=False),
        sa.Column("base_fee_wei", sa.Numeric(30, 0), nullable=True),
        sa.Column("eth_usd_price", sa.Numeric(20, 2), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
    )

    # CryptoRank market data
    op.create_table(
        "cryptorank_market_data",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("price_usd", sa.Numeric(20, 8), nullable=False),
        sa.Column("market_cap_usd", sa.Numeric(30, 2), nullable=True),
        sa.Column("volume_24h_usd", sa.Numeric(30, 2), nullable=True),
        sa.Column("change_1h_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("change_24h_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("change_7d_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timestamp"),
    )
    op.create_index("idx_cryptorank_rank", "cryptorank_market_data", ["rank"])


def downgrade() -> None:
    op.drop_table("cryptorank_market_data")
    op.drop_table("etherscan_gas_stats")
    op.drop_table("mempool_data")
```

**Run migration**:
```bash
cd src/etl
alembic upgrade head
```

---

## 7. Environment Variables

**Update** `.env.example`:

```bash
# Etherscan (get free key at https://etherscan.io/apis)
ETHERSCAN_API_KEY=YourApiKeyHere

# CryptoRank Sandbox (get at https://cryptorank.io/public-api)
CRYPTORANK_API_KEY=YourSandboxKeyHere

# Collectors
MEMPOOL_API_TIMEOUT=30
ETHERSCAN_API_TIMEOUT=30
CRYPTORANK_API_TIMEOUT=30
```

---

## 8. Testing All Collectors

```bash
# Unit tests
pytest tests/unit/collectors/test_mempool.py -v
pytest tests/unit/collectors/test_etherscan.py -v
pytest tests/unit/collectors/test_cryptorank.py -v

# Full coverage check
pytest tests/unit/collectors/ --cov=src/etl/collectors --cov-fail-under=80

# Integration tests (requires Docker Compose)
docker-compose up -d timescaledb
pytest tests/integration/ -v
docker-compose down
```

---

## 9. Manual Testing (CLI)

```python
# Python REPL
import asyncio
from src.etl.collectors.mempool import MempoolCollector
from src.etl.collectors.etherscan import EtherscanCollector
from src.etl.collectors.cryptorank import CryptoRankCollector

async def test_all():
    # Mempool
    async with MempoolCollector() as mem:
        block = await mem.fetch_latest_block()
        print(f"Latest BTC block: {block.block_height}, {block.tx_count} txs")

    # Etherscan
    async with EtherscanCollector() as eth:
        stats = await eth.fetch_gas_stats()
        print(f"ETH gas: {stats.standard_gas_gwei} gwei, ${stats.eth_usd_price}")

    # CryptoRank
    async with CryptoRankCollector() as cr:
        coins = await cr.fetch_all_coins(limit=5)
        for coin in coins:
            print(f"#{coin['rank']}: {coin['symbol']} ${coin['price_usd']}")

asyncio.run(test_all())
```

---

## 10. Rollout Checklist

- [ ] Create collectors (`mempool.py`, `etherscan.py`, `cryptorank.py`)
- [ ] Create Pydantic models in `src/shared/models/onchain.py`
- [ ] Create Alembic migration `202603_add_onchain_sources.py`
- [ ] Update `.env.example` with API keys
- [ ] Update `src/shared/config.py` with new fields
- [ ] Update scheduler with 3 new jobs
- [ ] Write unit tests (≥80% coverage)
- [ ] Run integration tests on Docker Compose
- [ ] Code review (no hardcoded secrets, proper error handling)
- [ ] Commit: `feat(etl): implement on-chain data sources (mempool, etherscan, cryptorank)`
- [ ] Create PR and merge to main

