# Data Sources Roadmap — Missing Implementations

**Author**: Analyst Data Sources (BMAD team)
**Date**: 2026-03-14
**Status**: Research & Specification for Sprint 5+

---

## Executive Summary

Current state: **67% compliance**, **4/10 data sources** (40% score).

This document specifies **6 missing data sources** for CryptoBot to reach full compliance:
1. **On-chain data** (Etherscan, Blockchain.com, Mempool.space)
2. **Regulatory data** (ESMA, SEC)
3. **News aggregators** (Phoenix News, CryptoRank)
4. **HTML scraping architecture** (BeautifulSoup pattern)

---

## Sources Prioritization Matrix

| Priority | Source | Effort | Value | Sprint | Decision |
|----------|--------|--------|-------|--------|----------|
| **P1** | Mempool.space (Bitcoin on-chain) | 2d | 9/10 | 5 | Free API, no auth, JSON REST |
| **P1** | Etherscan (Ethereum on-chain) | 3d | 9/10 | 5 | Free tier: 5 req/s, 100k/day |
| **P1** | Blockchain.com (Bitcoin wallets/tx) | 2d | 8/10 | 5 | Free, REST + WebSocket |
| **P2** | CryptoRank (aggregated data) | 2d | 7/10 | 6 | Sandbox: 100 req/min, 10k/month |
| **P2** | ESMA regulatory data | 4d | 6/10 | 7 | Scraping EU registry, no real API |
| **P3** | BeautifulSoup scraping layer | 3d | 7/10 | 5 | Generic HTML parser for ad-hoc sources |
| ~~P4~~ | ~~Phoenix News API~~ | ~~N/A~~ | ~~5/10~~ | ~~N/A~~ | **NOT RECOMMENDED**: No public API tier found (docs link dead) |

**Effort scale**: 1d = 1 developer-day, includes testing + migration
**Value**: Impact on signal generation confidence (0-10)

---

## Architecture Pattern — Existing vs. New

### Current Pattern (Working)

```python
# src/etl/collectors/binance.py — TEMPLATE
class BinanceCollector:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(...)  # Singleton HTTP client

    async def fetch_ohlcv(self, symbol: str, tf: str) -> list[OHLCVRecord]:
        # 1. Validate inputs
        # 2. with_retry() exponential backoff (5 attempts)
        # 3. Parse response → Pydantic models
        # 4. Validate constraints
        return records
```

**Key requirements for all new collectors**:
- `async/await` with `httpx.AsyncClient` (connection pooling)
- `Pydantic` validation at boundaries
- `with_retry()` helper for transient errors
- `logging.getLogger(__name__)` for structured logs
- Rate limit handling (429 status → `RateLimitError`)
- Network timeout: 30s total, 10s connect

---

## On-Chain Data Sources

### 1. Mempool.space API (Bitcoin)

**Priority**: P1 — "Must have for BTC analysis"

#### Endpoint Specs

```
Base: https://api.mempool.space
Free tier: Unlimited (no auth required)
Rate limit: Respect robots.txt, ~1 req/sec soft limit

GET /api/v1/blocks                    # Latest blocks + stats
GET /api/v1/blocks/tip/height         # Current block height
GET /api/v1/blocks/{block_hash}       # Block details
GET /api/v1/address/{address}         # Address balance, txs
GET /api/v1/tx/{txid}                 # Transaction details
GET /api/v1/tx/{txid}/outspends       # UTXO spend status
GET /api/mempool                      # Mempool stats (fees, size)
```

#### Data Format

**Response** (JSON):
```json
{
  "blocks": [
    {
      "id": "0000....",
      "timestamp": 1710345600,
      "height": 834567,
      "size": 1048576,
      "weight": 4000000,
      "tx_count": 3000,
      "total_in": "50.12345678",
      "total_out": "49.98765432",
      "totalFees": "0.13580246",
      "avgFee": 45000,
      "coinbaseRaw": "...",
      "version": 536870912,
      "merkleRoot": "...",
      "bits": 386089856,
      "difficulty": 99000000000,
      "medianTime": 1710345000,
      "nonce": 3844250607
    }
  ],
  "mempool": {
    "count": 12500,
    "vsize": 450000,
    "total_fee": 1250000,
    "fee_calc": {
      "1": 85000,
      "3": 78000,
      "6": 65000,
      "12": 45000
    }
  }
}
```

#### New Pydantic Model

```python
# src/shared/models/onchain.py
class MempoolBlockStats(BaseModel):
    block_hash: str
    height: int
    timestamp: datetime
    tx_count: int
    total_volume_btc: Decimal  # total_in
    total_fees_btc: Decimal
    avg_fee_satoshi: int
    difficulty: Decimal
    mempool_count: int | None = None  # Only in mempool stats
    mempool_vsize_mb: Decimal | None = None

class MempoolRecord(BaseModel):
    symbol: str = "BTCUSD"  # For consistency with OHLCVRecord
    timestamp: datetime
    block_height: int
    tx_count: int
    volume_btc: Decimal
    fee_satoshi_per_vbyte: int  # Current median fee
    source: str = "mempool.space"
    metadata: dict = Field(default_factory=dict)  # fee_calc, difficulty, etc.
```

#### Storage

**New table** or extend `crypto_prices`:
```sql
CREATE TABLE IF NOT EXISTS mempool_data (
    symbol VARCHAR(10),              -- BTCUSD
    timestamp TIMESTAMPTZ NOT NULL,
    block_height INTEGER,
    tx_count INTEGER,
    volume_btc DECIMAL(20, 8),
    fee_satoshi_per_vbyte INTEGER,
    avg_block_time_sec INTEGER,
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX idx_mempool_height ON mempool_data (block_height DESC);
```

**Or map to OHLCVRecord**:
- `symbol = "BTCUSD"`
- `price_open/high/low/close = fee_satoshi_per_vbyte` (as pseudo-price)
- `volume_24h = tx_count`
- `timeframe = "1h"` or `"1D"` (block time ~10min → aggregate hourly)

#### Rate Limits & Constraints

- **Rate limit**: Soft ~1 req/sec (no hard limit published)
- **Retry strategy**: 3s backoff, max 5 attempts
- **Timeout**: 30s total, 10s connect
- **Robots.txt compliance**: Check `mempool.space/robots.txt` (likely allows)
- **Free tier**: Unlimited, no API key required

#### Frequency

- Blocks: **5-10 minutes** (real-time: every new block ~10min avg)
- Mempool stats: **1 minute** (fee market changes rapidly)

#### Implementation Sketch

```python
# src/etl/collectors/mempool.py
class MempoolCollector:
    async def fetch_latest_block(self) -> MempoolRecord:
        # GET /api/v1/blocks/tip/height → latest block
        # GET /api/v1/blocks?start_index=0 → last block details
        pass

    async def fetch_mempool_stats(self) -> MempoolRecord:
        # GET /api/mempool → fee tiers, count, vsize
        pass

    async def fetch_address_balance(self, address: str) -> dict:
        # Optional: whale transaction tracking
        pass
```

---

### 2. Etherscan API (Ethereum + Multi-chain)

**Priority**: P1 — "Must have for ETH/EVM analysis"

#### Endpoint Specs

```
Base: https://api.etherscan.io
Free tier: 5 req/sec, 100k req/day
Auth: Requires API key (free registration)

GET /api?module=account&action=balance&address=...
GET /api?module=stats&action=ethprice
GET /api?module=gastracker&action=gasoracle
GET /api?module=stats&action=tokensupply&contractaddress=...
GET /api?module=proxy&action=eth_blockNumber
GET /api?module=logs&action=getLogs&fromBlock=...&toBlock=...
```

#### Data Format

**Response** (JSON):
```json
{
  "status": "1",
  "message": "OK",
  "result": {
    "SafeGasPrice": "45",
    "ProposeGasPrice": "50",
    "FastGasPrice": "60",
    "suggestBaseFeeper": "35",
    "UsdPrice": "4500.25"
  }
}
```

#### New Pydantic Model

```python
# src/shared/models/onchain.py
class EtherscanGasStats(BaseModel):
    symbol: str = "ETHUSD"
    timestamp: datetime
    safe_gas_price_gwei: Decimal
    standard_gas_price_gwei: Decimal
    fast_gas_price_gwei: Decimal
    base_fee_wei: Decimal
    eth_usd_price: Decimal
    source: str = "etherscan"
    metadata: dict = Field(default_factory=dict)

class EtherscanTokenStats(BaseModel):
    contract_address: str
    symbol: str
    total_supply: Decimal
    timestamp: datetime
    source: str = "etherscan"
```

#### Storage

**New table**:
```sql
CREATE TABLE IF NOT EXISTS etherscan_gas_stats (
    symbol VARCHAR(20),              -- ETHUSD
    timestamp TIMESTAMPTZ NOT NULL,
    safe_gas_gwei DECIMAL(10, 2),
    standard_gas_gwei DECIMAL(10, 2),
    fast_gas_gwei DECIMAL(10, 2),
    base_fee_wei DECIMAL(30, 0),
    eth_usd_price DECIMAL(20, 2),
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (symbol, timestamp)
);
```

#### Rate Limits & Constraints

- **Rate limit**: 5 req/sec, 100k req/day (soft cap)
- **Requires free API key**: https://etherscan.io/apis
- **Retry strategy**: Backoff 2s, max 3 attempts (rate limit is strict)
- **Timeout**: 30s total, 10s connect
- **Free tier restrictions** (2026): Ethereum mainnet only (full coverage). Other chains (Arbitrum, Optimism, Base) require paid Lite plan

#### Frequency

- Gas stats: **1-2 minutes** (market changes with blocks)
- Token supply: **Hourly** (rarely changes)

#### Implementation Sketch

```python
# src/etl/collectors/etherscan.py
class EtherscanCollector:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(...)
        self._api_key = api_key

    async def fetch_gas_stats(self) -> EtherscanGasStats:
        # GET /api?module=gastracker&action=gasoracle&apikey=...
        pass

    async def fetch_eth_price(self) -> Decimal:
        # GET /api?module=stats&action=ethprice&apikey=...
        pass
```

---

### 3. Blockchain.com API (Bitcoin + Bitcoin Cash)

**Priority**: P1 — "BTC wallet/tx data complements Mempool"

#### Endpoint Specs

```
Base: https://blockchain.info/api
Free tier: Unlimited (no auth)
Rate limit: Soft ~10 req/sec

GET /q/latestblock                   # Latest block
GET /q/getblockcount                 # Current height
GET /ticker                          # BTC/USD price
GET /address/{address}               # Wallet balance + txs
GET /tx/{txid}                       # Transaction details
GET /q/hashrate                      # Network hashrate
```

#### Data Format

**Response** (JSON):
```json
{
  "timestamp": 1710345600,
  "hash": "0000....",
  "height": 834567,
  "n_tx": 3000,
  "miner_reward": 625000000,
  "bits": "18030e08",
  "difficulty": 99000000000
}
```

#### New Pydantic Model

```python
# Use MempoolRecord or create BlockchainRecord
class BlockchainBTCStats(BaseModel):
    symbol: str = "BTCUSD"
    timestamp: datetime
    block_height: int
    tx_count: int
    hashrate_exahash: Decimal
    miner_reward_satoshi: int
    price_usd: Decimal
    source: str = "blockchain.com"
    metadata: dict = Field(default_factory=dict)
```

#### Storage

Use same `mempool_data` table or extend with hashrate field.

#### Rate Limits & Constraints

- **Rate limit**: Soft ~10 req/sec (no hard limit)
- **Free tier**: No API key required, unlimited
- **Retry strategy**: 2s backoff, max 5 attempts
- **Timeout**: 30s total, 10s connect

#### Frequency

- Block data: **10 minutes** (same as Mempool)
- Price ticker: **1 minute**

#### Implementation Sketch

```python
# src/etl/collectors/blockchain_com.py
class BlockchainComCollector:
    async def fetch_latest_block(self) -> BlockchainBTCStats:
        # GET /q/latestblock
        pass

    async def fetch_hashrate(self) -> Decimal:
        # GET /q/hashrate
        pass
```

---

## Aggregated Data Sources

### 4. CryptoRank API

**Priority**: P2 — "Aggregated signals + ICO tracking"

#### Endpoint Specs

```
Base: https://api.cryptorank.io
Free Sandbox: 100 req/min, 10k req/month, 14 endpoints
Auth: Requires free API key

GET /v1/coins                        # All coins
GET /v1/coins/{id}                   # Coin details
GET /v1/coins/{id}/chart             # Historical price
GET /v1/icos                         # ICO/token launches
GET /v1/news                         # Aggregated news
GET /v1/exchanges                    # Exchange list
```

#### Data Format

**Response** (JSON):
```json
{
  "id": "ethereum",
  "symbol": "ETH",
  "name": "Ethereum",
  "rank": 2,
  "price": 3750.50,
  "priceUSD": 3750.50,
  "marketCap": 450000000000,
  "volume24h": 25000000000,
  "change1h": 0.5,
  "change24h": 1.2,
  "change7d": 5.0
}
```

#### New Pydantic Model

```python
# src/shared/models/crypto.py (extend existing)
class CryptoRankCoin(BaseModel):
    symbol: str
    rank: int
    price_usd: Decimal
    market_cap_usd: Decimal
    volume_24h_usd: Decimal
    change_1h_pct: Decimal
    change_24h_pct: Decimal
    change_7d_pct: Decimal
    timestamp: datetime
    source: str = "cryptorank"
    metadata: dict = Field(default_factory=dict)
```

#### Storage

Extend `crypto_prices` table or create `cryptorank_market_data`:
```sql
CREATE TABLE IF NOT EXISTS cryptorank_market_data (
    symbol VARCHAR(20),
    timestamp TIMESTAMPTZ,
    rank INTEGER,
    price_usd DECIMAL(20, 8),
    market_cap_usd DECIMAL(30, 2),
    volume_24h_usd DECIMAL(30, 2),
    change_1h DECIMAL(10, 4),
    change_24h DECIMAL(10, 4),
    change_7d DECIMAL(10, 4),
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (symbol, timestamp)
);
```

#### Rate Limits & Constraints

- **Free Sandbox**: 100 req/min, 10k req/month, 14 endpoints
- **Requires API key**: Free registration at https://cryptorank.io/public-api
- **Rate limit strategy**: Queue requests, batch where possible
- **Retry strategy**: 3s backoff, max 3 attempts

#### Frequency

- Market data: **5 minutes** (matches CoinGecko cadence)
- ICO list: **Daily**

#### Implementation Sketch

```python
# src/etl/collectors/cryptorank.py
class CryptoRankCollector:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})

    async def fetch_all_coins(self) -> list[CryptoRankCoin]:
        # GET /v1/coins?limit=30&sort=rank
        pass
```

---

## Regulatory Data Sources

### 5. ESMA Crypto-Assets Registry (MiCA)

**Priority**: P2 — "Regulatory compliance tracking"

#### Data Source

```
Base: https://register.esma.europa.eu/
Method: HTML scraping (no machine-readable API published)

Endpoints:
- https://register.esma.europa.eu/publication?core=esma_official_list_of_cas
  (Official list of CASP — Crypto-Asset Service Providers)

- https://register.esma.europa.eu/publication?core=esma_official_list_acsps
  (Authorized Crypto-Asset Service Providers under MiCA)
```

#### Data Format

**HTML table** (requires BeautifulSoup scraping):
```html
<table>
  <tr>
    <td>Company Name</td>
    <td>Service Type</td>
    <td>Country</td>
    <td>Authorisation Status</td>
    <td>Link</td>
  </tr>
  <tr>
    <td>Kraken Europe</td>
    <td>Crypto Exchange</td>
    <td>DE</td>
    <td>Authorised</td>
    <td>https://...</td>
  </tr>
</table>
```

#### New Pydantic Model

```python
# src/shared/models/regulatory.py
class ESMAProvider(BaseModel):
    company_name: str
    service_type: str  # Exchange, Wallet, Custody, etc.
    country: str      # ISO 2-letter code
    authorization_status: str  # Authorised, Pending, Rejected, Withdrawn
    mica_compliant: bool
    registration_date: datetime | None
    url: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "esma"
    metadata: dict = Field(default_factory=dict)
```

#### Storage

**New table**:
```sql
CREATE TABLE IF NOT EXISTS regulatory_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(500),
    service_type VARCHAR(100),
    country VARCHAR(2),
    authorization_status VARCHAR(50),
    mica_compliant BOOLEAN,
    registration_date TIMESTAMPTZ,
    url VARCHAR(1000),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    UNIQUE(company_name, country)
);
```

#### Rate Limits & Constraints

- **Rate limit**: No API; scraping only. Respect robots.txt (1-2s delay)
- **Data freshness**: Weekly scrape (ESMA updates registry ~weekly)
- **Anti-bot**: User-Agent required, rotate headers
- **Failure handling**: Log scrape errors, skip + retry next day

#### Frequency

- **Weekly** (low change frequency)

#### Implementation Sketch

```python
# src/etl/collectors/esma.py
class ESMACollector:
    async def fetch_authorized_providers(self) -> list[ESMAProvider]:
        # GET https://register.esma.europa.eu/...
        # Parse HTML with BeautifulSoup
        # Extract table rows → ESMAProvider models
        pass
```

---

### 6. SEC EDGAR Filings (US Regulatory)

**Priority**: P3 (lower) — "US-focused regulatory signals"

#### Data Source

```
Base: https://data.sec.gov/api/
Method: REST API (JSON)

Endpoints:
GET /submissions/CIK0001657412    # SEC.gov structured API
GET /cgi-bin/browse-edgar?action=getcompany&CIK=...&type=&dateb=&owner=exclude&count=100
```

Note: SEC EDGAR is not crypto-specific; would require filtering for crypto-related filings (exchanges, custody, issuers).

#### Decision

**DEFER to Phase 2** (low value for Phase 1 scope). Crypto is regulated under MiCA in EU (ESMA) more directly than SEC.

---

## HTML Scraping Architecture

### 7. BeautifulSoup Generic Scraper Layer

**Priority**: P3 — "Foundation for ad-hoc sources"

#### Pattern

```python
# src/etl/collectors/scraper_base.py
from bs4 import BeautifulSoup
import httpx
from typing import Callable, TypeVar

T = TypeVar('T')

class HTMLScraper:
    """Base class for robust HTML scraping with retry + rate limit."""

    def __init__(self, base_url: str, delay_sec: float = 1.0) -> None:
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",  # Rotate
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )
        self._delay_sec = delay_sec
        self._last_request_at = 0.0

    async def fetch_and_parse(
        self,
        url: str,
        parser: Callable[[BeautifulSoup], T],
    ) -> T:
        """Fetch URL with rate limiting and parse with BeautifulSoup."""
        # Enforce rate limit (delay_sec between requests)
        elapsed = time() - self._last_request_at
        if elapsed < self._delay_sec:
            await asyncio.sleep(self._delay_sec - elapsed)

        response = await with_retry(
            lambda: self._client.get(url),
            max_attempts=5,
            base_delay=2.0,
            exceptions=(httpx.TransportError, httpx.TimeoutException, httpx.HTTPStatusError),
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        self._last_request_at = time()
        return parser(soup)


# Example: Decrypt.co scraper
class DecryptScraper(HTMLScraper):
    async def fetch_articles(self) -> list[NewsArticle]:
        def parse(soup: BeautifulSoup) -> list[NewsArticle]:
            articles = []
            for article_div in soup.find_all('article', class_='post'):
                title = article_div.find('h2', class_='post-title')
                link = article_div.find('a', class_='post-link')
                content = article_div.find('div', class_='post-excerpt')
                published = article_div.find('time')

                if title and link:
                    articles.append(NewsArticle(
                        title=title.get_text(strip=True),
                        url=link['href'],
                        content=content.get_text(strip=True) if content else None,
                        source="decrypt",
                        published_at=datetime.fromisoformat(published.get('datetime')) if published else None,
                    ))
            return articles

        return await self.fetch_and_parse("https://decrypt.co", parse)
```

#### Key Safeguards

1. **User-Agent rotation**: Randomize from pool of real user agents
2. **Rate limiting**: 1-2s delay between requests, per site
3. **Robots.txt compliance**: Check before scraping
4. **Graceful degradation**: Log errors, skip malformed entries, continue
5. **Timeouts**: 30s total, 10s connect per request
6. **Retry strategy**: 3x attempts with exponential backoff
7. **Circuit breaker**: If 3 consecutive failures, skip source for 1h

#### Integration with ETL Pipeline

```python
# src/etl/collectors/__init__.py
async def collect_news() -> list[NewsArticle]:
    """Collect news from all sources: RSS + scrapers."""
    articles = []

    # Existing RSS feeds
    async with NewsCollector() as rss:
        articles.extend(await rss.fetch_news())

    # New HTML scrapers
    decrypt_scraper = DecryptScraper(base_url="https://decrypt.co", delay_sec=1.0)
    articles.extend(await decrypt_scraper.fetch_articles())

    cointelegraph_scraper = CointelegraphScraper(delay_sec=1.5)
    articles.extend(await cointelegraph_scraper.fetch_articles())

    return articles
```

---

## Database Schema Changes

### New Tables

#### 1. Mempool Data (Bitcoin on-chain)

```sql
CREATE TABLE IF NOT EXISTS mempool_data (
    symbol VARCHAR(10) NOT NULL,           -- BTCUSD
    timestamp TIMESTAMPTZ NOT NULL,
    block_height INTEGER,
    tx_count INTEGER,
    volume_btc DECIMAL(20, 8),
    fee_satoshi_per_vbyte INTEGER,
    difficulty DECIMAL(30, 0),
    avg_block_time_sec INTEGER,
    source VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX idx_mempool_block_height ON mempool_data (block_height DESC);
CREATE INDEX idx_mempool_symbol_ts ON mempool_data (symbol, timestamp DESC);
```

#### 2. Etherscan Gas Stats (Ethereum on-chain)

```sql
CREATE TABLE IF NOT EXISTS etherscan_gas_stats (
    symbol VARCHAR(20) NOT NULL,           -- ETHUSD, GWEI
    timestamp TIMESTAMPTZ NOT NULL,
    safe_gas_gwei DECIMAL(10, 2),
    standard_gas_gwei DECIMAL(10, 2),
    fast_gas_gwei DECIMAL(10, 2),
    base_fee_wei DECIMAL(30, 0),
    eth_usd_price DECIMAL(20, 2),
    source VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX idx_etherscan_ts ON etherscan_gas_stats (timestamp DESC);
```

#### 3. CryptoRank Market Data

```sql
CREATE TABLE IF NOT EXISTS cryptorank_market_data (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    rank_by_market_cap INTEGER,
    price_usd DECIMAL(20, 8),
    market_cap_usd DECIMAL(30, 2),
    volume_24h_usd DECIMAL(30, 2),
    change_1h_pct DECIMAL(10, 4),
    change_24h_pct DECIMAL(10, 4),
    change_7d_pct DECIMAL(10, 4),
    source VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX idx_cryptorank_symbol ON cryptorank_market_data (symbol, timestamp DESC);
```

#### 4. ESMA Regulatory Providers

```sql
CREATE TABLE IF NOT EXISTS regulatory_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(500) NOT NULL,
    service_type VARCHAR(100),            -- Exchange, Wallet, Custody, etc.
    country VARCHAR(2),
    authorization_status VARCHAR(50),     -- Authorised, Pending, Rejected, etc.
    mica_compliant BOOLEAN DEFAULT false,
    registration_date TIMESTAMPTZ,
    url VARCHAR(1000),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    UNIQUE(company_name, country, service_type)
);
CREATE INDEX idx_regulatory_status ON regulatory_providers (authorization_status, country);
```

### Alternative: Extend crypto_prices

If storage simplicity is preferred, map all on-chain metrics to `crypto_prices` hypertable:

```sql
-- Extend existing crypto_prices schema
ALTER TABLE crypto_prices ADD COLUMN IF NOT EXISTS
    metadata_onchain JSONB DEFAULT '{}';  -- Store {block_height, tx_count, fee_gwei, etc.}
```

**Recommendation**: Create separate tables. `crypto_prices` is optimized for OHLCV (time-series); on-chain data is sparse and has different cardinality.

---

## New Pydantic Models

Location: `src/shared/models/` — create new files for modularity

```python
# src/shared/models/onchain.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class MempoolRecord(BaseModel):
    symbol: str = "BTCUSD"
    timestamp: datetime
    block_height: int
    tx_count: int
    volume_btc: Decimal
    fee_satoshi_per_vbyte: int
    difficulty: Decimal
    source: str = "mempool.space"
    metadata: dict = Field(default_factory=dict)

class EtherscanGasStats(BaseModel):
    symbol: str = "GWEI"
    timestamp: datetime
    safe_gas_gwei: Decimal
    standard_gas_gwei: Decimal
    fast_gas_gwei: Decimal
    base_fee_wei: Decimal
    eth_usd_price: Decimal
    source: str = "etherscan"
    metadata: dict = Field(default_factory=dict)

# src/shared/models/regulatory.py
class ESMAProvider(BaseModel):
    company_name: str
    service_type: str
    country: str
    authorization_status: str
    mica_compliant: bool
    registration_date: datetime | None = None
    url: str
    timestamp: datetime
    source: str = "esma"
    metadata: dict = Field(default_factory=dict)
```

---

## Alembic Migration Template

```python
# src/etl/migrations/versions/202603_add_onchain_sources.py
"""Add on-chain data tables for Mempool, Etherscan, CryptoRank.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0002"
down_revision: str | None = "0001"

def upgrade() -> None:
    # Mempool data (Bitcoin on-chain)
    op.create_table(
        "mempool_data",
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("block_height", sa.Integer, nullable=True),
        sa.Column("tx_count", sa.Integer, nullable=True),
        sa.Column("volume_btc", sa.Numeric(20, 8), nullable=True),
        sa.Column("fee_satoshi_per_vbyte", sa.Integer, nullable=True),
        sa.Column("difficulty", sa.Numeric(30, 0), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timestamp"),
    )
    op.create_index("idx_mempool_block_height", "mempool_data", ["block_height"], postgresql_using="btree")

    # Etherscan gas stats (Ethereum on-chain)
    op.create_table(
        "etherscan_gas_stats",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("safe_gas_gwei", sa.Numeric(10, 2), nullable=True),
        sa.Column("standard_gas_gwei", sa.Numeric(10, 2), nullable=True),
        sa.Column("fast_gas_gwei", sa.Numeric(10, 2), nullable=True),
        sa.Column("base_fee_wei", sa.Numeric(30, 0), nullable=True),
        sa.Column("eth_usd_price", sa.Numeric(20, 2), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timestamp"),
    )

    # ESMA regulatory providers
    op.create_table(
        "regulatory_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("service_type", sa.String(100), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("authorization_status", sa.String(50), nullable=True),
        sa.Column("mica_compliant", sa.Boolean, default=False),
        sa.Column("registration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        sa.UniqueConstraint("company_name", "country", "service_type", name="uq_regulatory_provider"),
    )

def downgrade() -> None:
    op.drop_table("regulatory_providers")
    op.drop_table("etherscan_gas_stats")
    op.drop_table("mempool_data")
```

---

## Implementation Checklist

### Sprint 5 (On-Chain Sources)

- [ ] Create `src/etl/collectors/mempool.py` + tests
  - [ ] `MempoolCollector.fetch_latest_block()`
  - [ ] `MempoolCollector.fetch_mempool_stats()`
  - [ ] Retry logic + rate limiting
  - [ ] Pydantic validation

- [ ] Create `src/etl/collectors/etherscan.py` + tests
  - [ ] API key configuration in `src/shared/config.py`
  - [ ] `EtherscanCollector.fetch_gas_stats()`
  - [ ] `EtherscanCollector.fetch_eth_price()`
  - [ ] 429 rate limit handling

- [ ] Create `src/etl/collectors/blockchain_com.py` + tests
  - [ ] `BlockchainComCollector.fetch_latest_block()`
  - [ ] `BlockchainComCollector.fetch_hashrate()`

- [ ] Create Alembic migration: `202603_add_onchain_sources.py`
- [ ] Create `src/shared/models/onchain.py`
- [ ] Update ETL scheduler to include 3 new jobs:
  - [ ] `collect_mempool_data()` — 5 min
  - [ ] `collect_etherscan_gas()` — 2 min
  - [ ] `collect_blockchain_com()` — 10 min
- [ ] Unit tests: ≥80% coverage
- [ ] Integration tests: Docker Compose + TimescaleDB

### Sprint 6 (Aggregated + HTML Scraping)

- [ ] Create `src/etl/collectors/cryptorank.py` + tests
  - [ ] API key in config
  - [ ] `CryptoRankCollector.fetch_all_coins()`

- [ ] Create `src/etl/collectors/scraper_base.py`
  - [ ] `HTMLScraper` base class
  - [ ] Rate limiting + user-agent rotation
  - [ ] Circuit breaker for failures

- [ ] Create `src/etl/collectors/decrypt_scraper.py`
  - [ ] Subclass `HTMLScraper`
  - [ ] Parse Decrypt.co articles

- [ ] Create `src/etl/collectors/cointelegraph_scraper.py`
  - [ ] Subclass `HTMLScraper`
  - [ ] Parse Cointelegraph articles

- [ ] Update `collect_news()` job to include scrapers
- [ ] Unit tests: ≥80% coverage

### Sprint 7 (Regulatory)

- [ ] Create `src/etl/collectors/esma.py`
  - [ ] `ESMACollector.fetch_authorized_providers()`
  - [ ] BeautifulSoup HTML parsing

- [ ] Create Alembic migration: add `regulatory_providers` table
- [ ] Create `src/shared/models/regulatory.py`
- [ ] Add scheduler job: `collect_regulatory_data()` — daily
- [ ] Unit tests: ≥80% coverage

---

## Config Changes

### src/shared/config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing...

    # On-chain sources
    MEMPOOL_API_TIMEOUT: int = 30
    ETHERSCAN_API_KEY: str = Field(default="", description="Free API key from etherscan.io")
    ETHERSCAN_API_TIMEOUT: int = 30
    BLOCKCHAIN_COM_API_TIMEOUT: int = 30

    # Aggregated data
    CRYPTORANK_API_KEY: str = Field(default="", description="Free Sandbox key from cryptorank.io")
    CRYPTORANK_API_TIMEOUT: int = 30

    # Scraping
    SCRAPER_DELAY_SEC: float = 1.0  # Delay between requests per domain
    SCRAPER_USER_AGENT_POOL: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ]
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_CIRCUIT_BREAKER_THRESHOLD: int = 3  # Failures before disabling for 1h

    class Config:
        env_file = ".env"
        case_sensitive = True
```

### .env.example

```bash
# Etherscan (https://etherscan.io/apis)
ETHERSCAN_API_KEY=your_free_api_key

# CryptoRank Sandbox (https://cryptorank.io/public-api)
CRYPTORANK_API_KEY=your_sandbox_key

# Scraping
SCRAPER_DELAY_SEC=1.0
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/collectors/test_mempool.py
import pytest
from src.etl.collectors.mempool import MempoolCollector

@pytest.mark.asyncio
async def test_fetch_latest_block_success():
    """Happy path: fetch latest block."""
    collector = MempoolCollector()
    record = await collector.fetch_latest_block()
    assert record.symbol == "BTCUSD"
    assert record.block_height > 0
    assert record.tx_count >= 0
    await collector.close()

@pytest.mark.asyncio
async def test_fetch_latest_block_network_error_retries():
    """Network error triggers retry with backoff."""
    # Mock httpx.AsyncClient.get() to fail twice, then succeed
    pass

@pytest.mark.asyncio
async def test_fetch_mempool_stats_parses_fee_tiers():
    """Parse fee tier response correctly."""
    pass
```

### Integration Tests

```python
# tests/integration/test_etl_pipeline_onchain.py
@pytest.mark.asyncio
async def test_mempool_data_inserted_to_db():
    """Mempool collector → validation → DB insertion."""
    async with TestDB() as db:
        collector = MempoolCollector()
        records = await collector.fetch_latest_block()
        await insert_records(db, records)

        stored = await db.fetch("SELECT * FROM mempool_data WHERE symbol='BTCUSD'")
        assert len(stored) == 1
        assert stored[0]['block_height'] > 0
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Etherscan free tier rate limit (5 req/sec)** | HIGH | Queue requests, batch gas stats queries, cache results |
| **HTML scraper DOM changes** | MEDIUM | Use CSS selectors + regex fallback, log failures, human review |
| **Mempool.space API downtime** | MEDIUM | Fall back to Blockchain.com, monitor uptime |
| **ESMA registry scraping complexity** | MEDIUM | Start with table parsing, handle exceptions per row |
| **CryptoRank Sandbox API quota (10k/month)** | LOW | Cache results 5 min, request upgrade if exceeded |
| **Regulatory data stale (scraped weekly)** | LOW | Accept weekly cadence; document in schema |

---

## Recommendations for MVP

### Phase 1 (High Value, Low Risk) — Implement ASAP

1. **Mempool.space** — Bitcoin on-chain data, no auth, stable API
2. **Blockchain.com** — BTC hashrate + network health, complements Mempool
3. **CryptoRank Sandbox** — Aggregated market data, easy integration

**Effort**: ~5 developer-days
**Value**: +30% to signal confidence (on-chain metrics + ranked market data)

### Phase 2 (Medium Value, Medium Risk) — Sprint 6

4. **Etherscan** — Ethereum gas tracking, requires API key management
5. **BeautifulSoup scraper layer** — Foundation for future ad-hoc sources

**Effort**: ~4 developer-days
**Value**: +20% (gas fees critical for timing)

### Phase 3 (Nice-to-Have, Higher Complexity) — Sprint 7

6. **ESMA regulatory data** — Compliance tracking, lower immediate signal value

**Effort**: ~3 developer-days (parsing is tricky)
**Value**: +10% (regulatory confidence)

### NOT Recommended

~~**Phoenix News API**~~ — No public free tier API found. The documentation link in the CLAUDE.md appears outdated. Alternative: Use free Crypto News API (newsdata.io) or expand BeautifulSoup scrapers instead.

---

## Next Steps

1. **Data team lead**: Review this spec with team, prioritize based on sprint capacity
2. **Backend team**: Review new Pydantic models in `src/shared/models/`, approve schema
3. **DevOps**: Update `.env.example` with new config keys, test API key provisioning
4. **Dev**: Create feature branch `data-eng/onchain-sources`, implement Phase 1 in priority order
5. **QA**: Run integration tests on Docker Compose (TimescaleDB + collectors)
6. **Review**: Code review + security audit (no hardcoded secrets, rate limits working)

---

## References

- [Mempool.space REST API](https://mempool.space/docs/api/rest)
- [Etherscan API Documentation](https://docs.etherscan.io/introduction)
- [Blockchain.com API](https://blockchain.info/api)
- [CryptoRank API Docs](https://api.cryptorank.io/docs/)
- [ESMA Registers](https://www.esma.europa.eu/publications-and-data/databases-and-registers)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/)
- [HTTPX Async Client](https://www.python-httpx.org/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)

