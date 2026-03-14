# BeautifulSoup Scraping Architecture

**Technical Design for HTML-based News & Regulatory Data Collection**

---

## Overview

Not all data sources provide REST APIs or RSS feeds. CryptoBot needs a robust, reusable HTML scraping layer to:

1. Extract articles from sources without RSS (e.g., Decrypt.co, Cointelegraph)
2. Parse regulatory registries (ESMA, SEC EDGAR)
3. Handle anti-bot protection gracefully
4. Respect rate limits and `robots.txt`
5. Fail gracefully without breaking the ETL pipeline

**Design principle**: Composition over inheritance. Each scraper is a thin adapter using a shared `HTMLScraper` base class with tested primitives.

---

## Architecture Pattern

### Layer 1: HTTP Client with Pooling

```python
# Shared httpx.AsyncClient with connection pooling
class HTTPClientManager:
    _instance: httpx.AsyncClient | None = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._instance is None:
            cls._instance = httpx.AsyncClient(
                headers={
                    "User-Agent": cls._get_random_user_agent(),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return cls._instance

    @staticmethod
    def _get_random_user_agent() -> str:
        # Rotate user agents to avoid being blocked
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(agents)
```

### Layer 2: Rate Limiter

```python
# Per-domain rate limiting to respect robots.txt
class RateLimiter:
    def __init__(self, delay_sec: float = 1.0) -> None:
        self._delay_sec = delay_sec
        self._last_request_at: dict[str, float] = {}  # domain -> timestamp

    async def wait(self, domain: str) -> None:
        """Enforce minimum delay between requests to the same domain."""
        now = time.time()
        last = self._last_request_at.get(domain, 0)
        elapsed = now - last

        if elapsed < self._delay_sec:
            await asyncio.sleep(self._delay_sec - elapsed)

        self._last_request_at[domain] = time.time()
```

### Layer 3: Circuit Breaker

```python
# Prevent hammer ing a broken source
class CircuitBreaker:
    def __init__(self, threshold: int = 3, timeout_sec: int = 3600) -> None:
        self._threshold = threshold
        self._timeout_sec = timeout_sec
        self._failures: dict[str, int] = {}
        self._broken_until: dict[str, float] = {}

    async def call(
        self,
        source_name: str,
        fn: Callable[[], Awaitable[T]],
    ) -> T | None:
        """Execute fn, return None if circuit is open."""
        now = time.time()

        # Check if circuit is open
        if source_name in self._broken_until:
            if now < self._broken_until[source_name]:
                logger.warning(f"Circuit breaker open for {source_name}, skipping")
                return None
            else:
                # Reset after timeout
                del self._broken_until[source_name]
                self._failures[source_name] = 0

        try:
            result = await fn()
            self._failures[source_name] = 0  # Reset on success
            return result
        except Exception as e:
            self._failures[source_name] = self._failures.get(source_name, 0) + 1
            logger.error(f"Scraper error {source_name}: {e}, failures: {self._failures[source_name]}")

            if self._failures[source_name] >= self._threshold:
                self._broken_until[source_name] = now + self._timeout_sec
                logger.error(f"Circuit breaker tripped for {source_name}, disabling for {self._timeout_sec}s")
            raise
```

### Layer 4: Base Scraper Class

```python
# src/etl/collectors/scraper_base.py
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Callable, Generic, TypeVar
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from src.shared.exceptions import ExternalAPIError
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

T = TypeVar('T')


class HTMLScraper(Generic[T]):
    """Base class for robust HTML scraping with retry, rate limit, circuit breaker."""

    def __init__(
        self,
        source_name: str,
        base_url: str,
        delay_sec: float = 1.0,
        parser: str = "html.parser",
    ) -> None:
        self._source_name = source_name
        self._base_url = base_url
        self._delay_sec = delay_sec
        self._parser = parser
        self._domain = urlparse(base_url).netloc

        self._rate_limiter = RateLimiter(delay_sec)
        self._circuit_breaker = CircuitBreaker(threshold=3, timeout_sec=3600)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create shared HTTP client."""
        if self._client is None:
            self._client = await HTTPClientManager.get_client()
        return self._client

    async def fetch_and_parse(
        self,
        url: str,
        parser_fn: Callable[[BeautifulSoup], list[T]],
    ) -> list[T]:
        """Fetch URL with rate limiting and parse HTML.

        Args:
            url: Full URL to scrape
            parser_fn: Function (BeautifulSoup → list[T]) to extract data

        Returns:
            List of parsed objects. Returns empty list if circuit breaker is open.

        Raises:
            ExternalAPIError: On persistent network/parse errors
        """
        async def scrape() -> list[T]:
            # Rate limit
            await self._rate_limiter.wait(self._domain)

            # Fetch with retry
            response: httpx.Response = await with_retry(
                lambda: self._get_client_and_fetch(url),
                max_attempts=5,
                base_delay=2.0,
                exceptions=(httpx.TransportError, httpx.TimeoutException, httpx.HTTPStatusError),
            )

            # Parse
            soup = BeautifulSoup(response.text, self._parser)
            results = parser_fn(soup)
            logger.info(f"{self._source_name}: parsed {len(results)} items from {url}")
            return results

        # Execute with circuit breaker
        result = await self._circuit_breaker.call(self._source_name, scrape)
        return result or []

    async def _get_client_and_fetch(self, url: str) -> httpx.Response:
        """Get client and fetch URL with error handling."""
        client = await self._get_client()
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except httpx.TransportError as exc:
            raise ExternalAPIError(
                f"Network error scraping {self._source_name}: {exc}",
                detail=str(exc),
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise ExternalAPIError(
                    f"Rate limited by {self._source_name} (HTTP 429)",
                    detail={"retry_after": exc.response.headers.get("Retry-After")},
                ) from exc
            raise ExternalAPIError(
                f"HTTP {exc.response.status_code} from {self._source_name}",
                detail=exc.response.text[:200],
            ) from exc


# Global circuit breaker (shared across all scrapers)
_GLOBAL_CIRCUIT_BREAKER = CircuitBreaker(threshold=3, timeout_sec=3600)
```

---

## Concrete Implementations

### Example 1: Decrypt.co Scraper

```python
# src/etl/collectors/decrypt_scraper.py
from __future__ import annotations

import logging
from datetime import UTC, datetime
from bs4 import BeautifulSoup

from src.etl.collectors.scraper_base import HTMLScraper
from src.shared.models.crypto import NewsArticle

logger = logging.getLogger(__name__)


class DecryptScraper(HTMLScraper[NewsArticle]):
    """Scrape articles from Decrypt.co."""

    def __init__(self) -> None:
        super().__init__(
            source_name="decrypt",
            base_url="https://decrypt.co",
            delay_sec=1.5,  # Respect robots.txt
        )

    async def fetch_articles(self) -> list[NewsArticle]:
        """Fetch latest articles from Decrypt homepage."""
        def parse(soup: BeautifulSoup) -> list[NewsArticle]:
            articles = []

            # Decrypt.co HTML structure (as of Mar 2026):
            # <article class="article-card">
            #   <h3><a href="/news/...">Title</a></h3>
            #   <time>2026-03-14T12:00Z</time>
            #   <p class="summary">Summary...</p>
            # </article>

            for article_elem in soup.find_all("article", class_="article-card"):
                try:
                    # Extract title
                    title_link = article_elem.find("h3", class_="article-title")
                    if not title_link or not title_link.find("a"):
                        logger.debug("Skipping article with missing title")
                        continue

                    title = title_link.get_text(strip=True)
                    url = title_link.find("a").get("href", "")
                    if not url.startswith("http"):
                        url = f"https://decrypt.co{url}"

                    # Extract timestamp
                    time_elem = article_elem.find("time")
                    published_at: datetime | None = None
                    if time_elem and time_elem.get("datetime"):
                        try:
                            published_at = datetime.fromisoformat(
                                time_elem.get("datetime").replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    # Extract summary
                    summary_elem = article_elem.find("p", class_="summary")
                    content = summary_elem.get_text(strip=True) if summary_elem else None

                    article = NewsArticle(
                        title=title,
                        url=url,
                        content=content,
                        source="decrypt",
                        published_at=published_at,
                    )
                    articles.append(article)
                    logger.debug(f"Parsed article: {title[:50]}")

                except (AttributeError, ValueError) as e:
                    logger.warning(f"Failed to parse article element: {e}")
                    continue

            return articles

        return await self.fetch_and_parse(
            f"{self._base_url}/latest",
            parse,
        )
```

### Example 2: ESMA Registry Scraper

```python
# src/etl/collectors/esma_scraper.py
from __future__ import annotations

import logging
from datetime import UTC, datetime
from bs4 import BeautifulSoup

from src.etl.collectors.scraper_base import HTMLScraper
from src.shared.models.regulatory import ESMAProvider

logger = logging.getLogger(__name__)


class ESMAScraper(HTMLScraper[ESMAProvider]):
    """Scrape authorized crypto providers from ESMA register."""

    def __init__(self) -> None:
        super().__init__(
            source_name="esma",
            base_url="https://register.esma.europa.eu",
            delay_sec=2.0,  # More conservative for regulatory data
        )

    async def fetch_authorized_providers(self) -> list[ESMAProvider]:
        """Fetch authorized CASP list from ESMA register."""
        def parse(soup: BeautifulSoup) -> list[ESMAProvider]:
            providers = []

            # ESMA register HTML structure:
            # <table class="register-table">
            #   <tr>
            #     <td>Company Name</td>
            #     <td>Service Type</td>
            #     <td>Country</td>
            #     <td>Status</td>
            #   </tr>
            # </table>

            table = soup.find("table", class_="register-table")
            if not table:
                logger.warning("ESMA register table not found, structure may have changed")
                return []

            rows = table.find_all("tr")[1:]  # Skip header row
            logger.info(f"ESMA: Found {len(rows)} provider rows")

            for row_idx, row in enumerate(rows):
                try:
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        logger.debug(f"Row {row_idx}: insufficient cells, skipping")
                        continue

                    company_name = cells[0].get_text(strip=True)
                    service_type = cells[1].get_text(strip=True)
                    country = cells[2].get_text(strip=True)
                    status = cells[3].get_text(strip=True)

                    # Extract detail link if present
                    detail_link = row.find("a")
                    url = detail_link.get("href", "") if detail_link else ""
                    if url and not url.startswith("http"):
                        url = f"https://register.esma.europa.eu{url}"

                    provider = ESMAProvider(
                        company_name=company_name,
                        service_type=service_type,
                        country=country,
                        authorization_status=status,
                        mica_compliant=(status.lower() == "authorised"),
                        url=url,
                        timestamp=datetime.now(UTC),
                    )
                    providers.append(provider)
                    logger.debug(f"Parsed provider: {company_name} ({country})")

                except (IndexError, AttributeError, ValueError) as e:
                    logger.warning(f"Failed to parse ESMA row {row_idx}: {e}")
                    continue

            return providers

        # ESMA publishes two lists; fetch both
        all_providers = []

        # List 1: Authorized CASPs
        logger.info("Fetching ESMA authorized CASP list")
        providers = await self.fetch_and_parse(
            f"{self._base_url}/publication?core=esma_official_list_acsps",
            parse,
        )
        all_providers.extend(providers)

        # List 2: Non-compliant entities (separate page)
        logger.info("Fetching ESMA non-compliant entities list")
        non_compliant = await self.fetch_and_parse(
            f"{self._base_url}/publication?core=esma_official_list_cas",
            parse,
        )
        all_providers.extend(non_compliant)

        logger.info(f"ESMA: Total {len(all_providers)} providers fetched")
        return all_providers
```

---

## Anti-Bot & Robustness Strategies

### 1. User-Agent Rotation

```python
# Implemented in HTTPClientManager._get_random_user_agent()
# Pools real browser user agents to avoid detection

REAL_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]
```

### 2. Rate Limiting Per Domain

```python
# Respect robots.txt + ethical scraping
class RateLimiter:
    _delay_sec: float = 1.0  # 1s between requests to same domain
    # Can be per-source, e.g. ESMA 2.0s, Decrypt 1.5s
```

### 3. Robots.txt Compliance Check

```python
# Optional: Check robots.txt before scraping
async def check_robots_txt(domain: str, path: str) -> bool:
    """Return True if robots.txt allows scraping this path."""
    try:
        resp = await client.get(f"https://{domain}/robots.txt", timeout=5.0)
        rules = robotparser.RobotFileParser()
        rules.parse(resp.text.splitlines())
        return rules.can_fetch("*", f"https://{domain}{path}")
    except Exception as e:
        logger.warning(f"Could not check robots.txt for {domain}: {e}")
        return True  # Default: proceed if check fails
```

### 4. Circuit Breaker (Auto-Disable on Repeated Failures)

```python
# After 3 consecutive failures, disable scraper for 1 hour
class CircuitBreaker:
    _threshold = 3
    _timeout_sec = 3600

    # Prevents hammering a broken site
    # Logs: "Circuit breaker tripped for decrypt, disabling for 3600s"
```

### 5. Graceful Error Handling

```python
# Fail individual articles, not the entire job
def parse(soup: BeautifulSoup) -> list[NewsArticle]:
    articles = []
    for article_elem in soup.find_all("article"):
        try:
            article = parse_article(article_elem)
            articles.append(article)
        except Exception as e:
            logger.warning(f"Skipping malformed article: {e}")
            continue  # Don't crash on one bad article
    return articles
```

### 6. Timeout Per Request

```python
# httpx.Timeout(30.0, connect=10.0)
# Total: 30s, connect: 10s
# Prevent hanging on slow servers
```

---

## Integration with ETL Pipeline

### Update collect_news() Job

```python
# src/etl/jobs/collect_news.py
async def collect_news() -> None:
    """Collect news from all sources: RSS feeds + HTML scrapers."""
    from src.etl.collectors.news import NewsCollector
    from src.etl.collectors.decrypt_scraper import DecryptScraper
    from src.etl.collectors.cointelegraph_scraper import CointelegraphScraper

    all_articles = []

    # Existing RSS feeds
    logger.info("Fetching RSS feeds")
    async with NewsCollector() as rss_collector:
        rss_articles = await rss_collector.fetch_news()
        all_articles.extend(rss_articles)
        logger.info(f"RSS: collected {len(rss_articles)} articles")

    # HTML scrapers
    logger.info("Fetching HTML-based news")
    try:
        decrypt = DecryptScraper()
        decrypt_articles = await decrypt.fetch_articles()
        all_articles.extend(decrypt_articles)
        logger.info(f"Decrypt: collected {len(decrypt_articles)} articles")
    except Exception as e:
        logger.error(f"Decrypt scraper failed: {e}", exc_info=True)

    try:
        cointelegraph = CointelegraphScraper()
        ct_articles = await cointelegraph.fetch_articles()
        all_articles.extend(ct_articles)
        logger.info(f"Cointelegraph: collected {len(ct_articles)} articles")
    except Exception as e:
        logger.error(f"Cointelegraph scraper failed: {e}", exc_info=True)

    # Dedup by URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article.url not in seen_urls:
            unique_articles.append(article)
            seen_urls.add(article.url)

    # Validate + insert
    logger.info(f"News collection: {len(unique_articles)} unique articles")
    await insert_news_articles(unique_articles)
```

### Scheduler Job

```python
# src/etl/scheduler.py
scheduler.add_job(
    collect_news,
    "interval",
    minutes=15,
    name="collect_news",
    max_instances=1,
    misfire_grace_time=300,
)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/collectors/test_decrypt_scraper.py
import pytest
from bs4 import BeautifulSoup
from src.etl.collectors.decrypt_scraper import DecryptScraper

def test_parse_articles_success():
    """Happy path: parse valid HTML."""
    html = """
    <article class="article-card">
        <h3 class="article-title">
            <a href="/news/bitcoin-rally">Bitcoin Rally Continues</a>
        </h3>
        <time datetime="2026-03-14T12:00:00Z"></time>
        <p class="summary">Market sentiment turns bullish.</p>
    </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = DecryptScraper()

    # Scraper has an internal parse function, extract for testing
    articles = scraper._parse(soup)  # or create a testable method

    assert len(articles) == 1
    assert articles[0].title == "Bitcoin Rally Continues"
    assert "bitcoin-rally" in articles[0].url

def test_parse_missing_title():
    """Malformed article: missing title."""
    html = """
    <article class="article-card">
        <time datetime="2026-03-14T12:00:00Z"></time>
    </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    # Should skip malformed article, return empty list
    assert scraper._parse(soup) == []

def test_rate_limiting():
    """Rate limiter enforces delay between requests."""
    # Mock time.time() to verify delay calculation
    pass

def test_circuit_breaker_trips():
    """After 3 failures, circuit breaker opens."""
    # Mock fetch to raise exception 3x
    # Verify 4th call returns None (circuit open)
    pass
```

### Integration Tests

```python
# tests/integration/test_news_scraping.py
@pytest.mark.asyncio
async def test_decrypt_scraper_fetch_real():
    """Scrape real Decrypt.co homepage (slow, integration only)."""
    scraper = DecryptScraper()
    articles = await scraper.fetch_articles()

    assert len(articles) > 0
    assert all(isinstance(a, NewsArticle) for a in articles)
    assert all(a.source == "decrypt" for a in articles)
    await scraper.close()

@pytest.mark.asyncio
async def test_news_collection_deduplication():
    """Collect news from multiple sources, deduplicate by URL."""
    # Mock RSS + scrapers to return known articles
    # Verify dedup removes URL duplicates
    pass
```

---

## Maintenance & Monitoring

### HTML Structure Changes

When a site redesigns, scraper breaks. **Action plan**:

1. **Monitor error logs**: Look for "Skipping article" + "AttributeError"
2. **Alert threshold**: If >50% articles skipped for 2+ runs, flag for review
3. **Manual inspection**: Developer visits site, updates CSS selectors
4. **Rollback**: Temporarily disable scraper, fall back to RSS if available

Example alert:
```python
# In collect_news job
skipped_pct = (total_rows - parsed_rows) / total_rows
if skipped_pct > 0.5:
    logger.error(f"Decrypt: {skipped_pct*100:.1f}% articles skipped, HTML structure may have changed!")
    # Send alert to Slack/email
```

### Robots.txt & Terms of Service

- **Check `robots.txt`** before initial implementation
- **Document delay**: Respect `Crawl-delay` directive (default 1-2s)
- **Review ToS**: Ensure scraping is permitted (most news sites allow it)

Example for Decrypt.co:
```
User-agent: *
Crawl-delay: 1
Allow: /
Disallow: /admin
```

→ Respect 1s delay, scrape `/` directory only.

---

## Configuration

### src/shared/config.py

```python
class Settings(BaseSettings):
    # Scraping configuration
    SCRAPER_DELAY_SEC: float = Field(default=1.0, description="Delay between requests per domain")
    SCRAPER_USER_AGENT_POOL: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
    ]
    SCRAPER_MAX_RETRIES: int = 5
    SCRAPER_RETRY_BASE_DELAY: float = 2.0
    SCRAPER_CIRCUIT_BREAKER_THRESHOLD: int = 3
    SCRAPER_CIRCUIT_BREAKER_TIMEOUT_SEC: int = 3600
```

---

## Example: Adding a New Scraper (Cointelegraph)

**Step 1**: Inspect HTML structure
```bash
curl https://cointelegraph.com | grep -A 5 "article"
# Identify CSS selectors for title, link, date, summary
```

**Step 2**: Create scraper class
```python
# src/etl/collectors/cointelegraph_scraper.py
class CointelegraphScraper(HTMLScraper[NewsArticle]):
    def __init__(self) -> None:
        super().__init__(
            source_name="cointelegraph",
            base_url="https://cointelegraph.com",
            delay_sec=1.5,
        )

    async def fetch_articles(self) -> list[NewsArticle]:
        def parse(soup: BeautifulSoup) -> list[NewsArticle]:
            # Similar to DecryptScraper
            # Use Cointelegraph-specific selectors
            pass
        return await self.fetch_and_parse(...)
```

**Step 3**: Add to collect_news()
```python
try:
    cointelegraph = CointelegraphScraper()
    articles = await cointelegraph.fetch_articles()
    all_articles.extend(articles)
except Exception as e:
    logger.error(f"Cointelegraph failed: {e}")
```

**Step 4**: Test + commit
```bash
pytest tests/unit/collectors/test_cointelegraph_scraper.py
git add -A && git commit -m "feat(etl): add cointelegraph HTML scraper"
```

---

## Risk Summary

| Risk | Mitigation |
|------|-----------|
| **Website structure changes** | Monitor error rate, alert on >50% skip rate, manual review + fix |
| **Rate limiting / blocking** | Respect robots.txt, use delays, rotate user-agents |
| **Terms of Service violation** | Review ToS for each site, document compliance decision |
| **Performance degradation** | Circuit breaker disables broken scrapers, prevents hammer loop |
| **Stale data** | Log parse failures separately from network errors, manual audit |

---

## References

- [BeautifulSoup4 documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Httpx async client](https://www.python-httpx.org/)
- [Python robotparser](https://docs.python.org/3/library/urllib.robotparser.html)
- [Web scraping best practices](https://blog.apify.com/web-scraping-best-practices/)

