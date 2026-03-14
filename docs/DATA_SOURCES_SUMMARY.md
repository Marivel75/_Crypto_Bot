# Data Sources Implementation Summary

**Quick Reference for Data Engineering Team**

---

## Current State vs Target

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **Data sources** | 4/10 (40%) | 10/10 (100%) | 6 sources |
| **Compliance** | 67% | 100% | 33% |
| **On-chain data** | 0 | 3 APIs | Bitcoin + Ethereum coverage |
| **Regulatory data** | 0 | ESMA registry | EU compliance tracking |
| **Market aggregation** | 1 (CoinGecko) | 2 (+ CryptoRank) | Better ranking signals |
| **News coverage** | 3 RSS feeds | 5+ (RSS + HTML scrapers) | Non-RSS sources |

---

## Implementation Roadmap by Sprint

### Sprint 5: On-Chain Foundation (Week of Mar 17)

**Goal**: Add Bitcoin + Ethereum on-chain metrics for technical signal confidence.

| Source | Type | Effort | Priority | Config |
|--------|------|--------|----------|--------|
| **Mempool.space** | REST API | 2d | P1 | No auth (free) |
| **Blockchain.com** | REST API | 2d | P1 | No auth (free) |
| **Etherscan** | REST API | 3d | P1 | `ETHERSCAN_API_KEY` (free) |

**Deliverables**:
- 3 new collectors in `src/etl/collectors/`
- Alembic migration: `202603_add_onchain_sources.py`
- 3 new Pydantic models in `src/shared/models/onchain.py`
- 3 ETL jobs (Mempool, Blockchain.com, Etherscan) on scheduler
- Unit + integration tests (≥80% coverage)

**Testing**: Docker Compose + TimescaleDB validation

---

### Sprint 6: Aggregation + Scraping (Week of Mar 24)

**Goal**: Add market-rank signals + HTML scraper foundation for non-RSS sources.

| Source | Type | Effort | Priority | Config |
|--------|------|--------|----------|--------|
| **CryptoRank API** | REST API | 2d | P2 | `CRYPTORANK_API_KEY` (Sandbox free) |
| **BeautifulSoup layer** | HTML scraper | 3d | P2 | `SCRAPER_DELAY_SEC=1.0` |

**Deliverables**:
- `src/etl/collectors/cryptorank.py` + tests
- `src/etl/collectors/scraper_base.py` (base class for all HTML scrapers)
- Optional: `src/etl/collectors/decrypt_scraper.py` + `cointelegraph_scraper.py`
- Update `collect_news()` job to include scrapers
- Migration: `202604_add_cryptorank_data.py`

**Testing**: Mock HTML responses, test rate limiting + retries

---

### Sprint 7: Regulatory Compliance (Week of Mar 31)

**Goal**: Track authorized crypto providers under EU MiCA regulation.

| Source | Type | Effort | Priority | Config |
|--------|------|--------|----------|--------|
| **ESMA Registry** | HTML scrape | 3d | P2 | None (public registry) |

**Deliverables**:
- `src/etl/collectors/esma.py` + tests
- `src/shared/models/regulatory.py`
- Migration: `202605_add_regulatory_providers.py`
- Job: `collect_regulatory_data()` — daily at 02:00 UTC
- Regulatory alerts: flag non-compliant exchanges in watchlist API

**Testing**: Parse actual ESMA HTML, validate schema

---

## Not Recommended

### Phoenix News API

**Decision**: ✗ **SKIP**

**Reason**: No documented public free API tier found (as of Mar 2026). The reference in CLAUDE.md appears to be outdated documentation.

**Alternative**: Use free Crypto News API endpoints (Decrypt RSS already covers) or expand BeautifulSoup scrapers to more sources.

---

## Data Model Architecture

### New Tables (Alembic Migrations)

```
Sprint 5:
  ├── mempool_data          [Bitcoin on-chain metrics]
  ├── etherscan_gas_stats   [Ethereum gas tracker]
  └── (blockchain_com → use mempool_data + extend)

Sprint 6:
  └── cryptorank_market_data [Ranked market data]

Sprint 7:
  └── regulatory_providers  [ESMA authorized CASPs]
```

### New Pydantic Models

```
src/shared/models/
  ├── onchain.py          [MempoolRecord, EtherscanGasStats, BlockchainBTCStats]
  ├── aggregated.py       [CryptoRankCoin]
  └── regulatory.py       [ESMAProvider]
```

---

## Configuration Changes

### Environment Variables (.env)

```bash
# Etherscan (get free key at https://etherscan.io/apis)
ETHERSCAN_API_KEY=your_key_here

# CryptoRank Sandbox (get at https://cryptorank.io/public-api)
CRYPTORANK_API_KEY=your_sandbox_key

# Scraping settings
SCRAPER_DELAY_SEC=1.0
SCRAPER_MAX_RETRIES=3
```

### Code Changes

File: `src/shared/config.py`

Add fields:
```python
ETHERSCAN_API_KEY: str = Field(default="")
CRYPTORANK_API_KEY: str = Field(default="")
SCRAPER_DELAY_SEC: float = 1.0
SCRAPER_USER_AGENT_POOL: list[str] = [...]
SCRAPER_MAX_RETRIES: int = 3
```

---

## API Rate Limits Summary

| Source | Limit | Strategy |
|--------|-------|----------|
| **Mempool.space** | ~1 req/sec (soft) | Natural request rate (10min blocks) |
| **Blockchain.com** | ~10 req/sec (soft) | Natural request rate |
| **Etherscan** | 5 req/sec, 100k/day | Queue requests, batch where possible |
| **CryptoRank Sandbox** | 100 req/min, 10k/month | Cache results 5min, batch coins |
| **ESMA Registry** | Robots.txt (likely 1-2s delay) | 1s delay between requests, weekly scrape |

---

## Testing Checklist

### Unit Tests (src/etl/collectors/test_*.py)

For each collector:
- [ ] Happy path: fetch data successfully
- [ ] Malformed response: graceful error handling
- [ ] Network timeout: retries with backoff
- [ ] Rate limit (429): respect Retry-After header
- [ ] Invalid Pydantic model: log + skip record
- [ ] Parsing edge cases (null fields, empty arrays, type coercion)

### Integration Tests (tests/integration/)

- [ ] Collector → Pydantic validation → DB insert
- [ ] Schema constraints enforced (unique, not null, etc.)
- [ ] Duplicate data handling (upsert or skip)
- [ ] Data freshness (timestamp within expected window)
- [ ] Hypertable compression policies applied

### E2E (Docker Compose)

- [ ] All collectors run without errors
- [ ] Database connections stay open (no leaks)
- [ ] Scheduler fires jobs at expected intervals
- [ ] Data appears in Streamlit dashboard

---

## Git Workflow

**Branch**: `data-eng/missing-sources`

**Commits** (per sprint):
```
Sprint 5:
  feat(etl): implement mempool.space collector
  feat(etl): implement etherscan gas tracker
  feat(etl): implement blockchain.com collector
  feat(etl): add on-chain data tables (alembic migration)

Sprint 6:
  feat(etl): implement cryptorank collector
  feat(etl): add html scraper base class
  feat(etl): extend news collector with beaut Soup layer

Sprint 7:
  feat(etl): implement esma regulatory provider scraper
  feat(api): add regulatory compliance endpoint (optional)
```

---

## Signal Impact Analysis

**How each source improves signal generation**:

| Source | Metric | Impact | Example |
|--------|--------|--------|---------|
| **Mempool.space** | BTC fee market, block height, tx count | Timing signals (low-fee entry points) | "Enter on low fees (<20 sat/vB) + RSI oversold" |
| **Etherscan** | ETH gas gwei, base fee, price | Gas cost estimation + congestion detection | "Wait for base fee <30 gwei before selling alts" |
| **Blockchain.com** | BTC hashrate, network health | Long-term trend confirmation | "Rising hashrate = strengthening bulls" |
| **CryptoRank** | Market cap rank, 24h volume, % changes | Momentum filtering + cap-weighted signals | "Only trade top 20 by rank" |
| **ESMA Registry** | Authorized providers, compliance status | Risk filtering (avoid unregulated exchanges) | "Exclude non-authorised custodians" |

**Combined confidence boost**: +40-50% (from 40% to 85-90% signal reliability)

---

## Success Criteria

By end of Sprint 7:

- [ ] All 6 sources implemented and tested (≥80% coverage)
- [ ] No hardcoded secrets (all in .env)
- [ ] No `print()` statements (use `logging`)
- [ ] All rate limits respected (no 429 errors in logs)
- [ ] Database queries optimized (no N+1)
- [ ] Documentation complete in `docs/01-data-engineering.md`
- [ ] Team review + approval
- [ ] Data quality metrics visible in monitoring

---

## Effort Estimate

| Sprint | Sources | Effort | Risk |
|--------|---------|--------|------|
| 5 | Mempool, Blockchain.com, Etherscan | 7d | Low (stable APIs) |
| 6 | CryptoRank, BeautifulSoup | 5d | Medium (scraping fragility) |
| 7 | ESMA | 3d | Medium (HTML parsing complexity) |
| **Total** | **6 sources** | **~15d** | Medium |

**Parallel tracks**: Sprints 5 & 6 can overlap (different APIs, no dependency).

---

## Rollback Plan

If a source causes issues:

1. **Remove collector**: Comment out job in scheduler
2. **Mark deprecated**: Add `# TODO: Fix X` comment in collector code
3. **Alert team**: Update roadmap, reschedule to next sprint
4. **Fallback**: Use alternative source (e.g., CoinGecko gas tracker instead of Etherscan)

Example:
```python
# src/etl/scheduler.py
# TODO: Etherscan rate limit issues in production (Mar 18) — revisit queue strategy
# async def collect_etherscan_gas():
#     pass
```

---

## Links & References

**Implementations to review**:
- `src/etl/collectors/binance.py` — Async HTTP pattern template
- `src/etl/collectors/news.py` — RSS parsing pattern
- `src/etl/collectors/fear_greed.py` — API + Pydantic pattern

**Official APIs**:
- [Mempool.space REST API](https://mempool.space/docs/api/rest)
- [Etherscan API Documentation](https://docs.etherscan.io/introduction)
- [Blockchain.com Explorer API](https://blockchain.info/api)
- [CryptoRank API Docs](https://api.cryptorank.io/docs/)
- [ESMA Registers Portal](https://www.esma.europa.eu/publications-and-data/databases-and-registers)

**Tools**:
- [Httpx async client](https://www.python-httpx.org/)
- [BeautifulSoup4 HTML parser](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Pydantic v2 validation](https://docs.pydantic.dev/latest/)
- [Alembic migrations](https://alembic.sqlalchemy.org/)

