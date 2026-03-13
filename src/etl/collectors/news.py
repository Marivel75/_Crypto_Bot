"""RSS news collector — parses crypto news feeds into NewsArticle models."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser  # type: ignore[import-untyped]
import httpx

from src.shared.models.crypto import NewsArticle

logger = logging.getLogger(__name__)

_DEFAULT_SOURCES: tuple[str, ...] = (
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://cryptonews.com/news/feed/",
)

_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class NewsCollector:
    """Async RSS news collector.

    Fetches raw RSS XML over HTTP, then uses feedparser for parsing.
    Uses a shared httpx.AsyncClient. Call ``await collector.close()``
    when finished, or use as an async context manager.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "crypto-bot/1.0 (RSS reader)"},
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> NewsCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_news(
        self,
        sources: list[str] | None = None,
    ) -> list[NewsArticle]:
        """Fetch and parse RSS feeds into NewsArticle models.

        Args:
            sources: List of RSS feed URLs to fetch. Defaults to
                     Decrypt and Cointelegraph if ``None``.

        Returns:
            Combined list of ``NewsArticle`` instances from all sources.
            Failed individual feeds are logged and skipped — they do not
            raise an exception so that the remaining feeds still succeed.
        """
        feed_urls = sources if sources is not None else list(_DEFAULT_SOURCES)
        articles: list[NewsArticle] = []

        for url in feed_urls:
            try:
                feed_articles = await self._fetch_feed(url)
                articles.extend(feed_articles)
                logger.info(
                    "News feed collected: url=%s articles=%d",
                    url,
                    len(feed_articles),
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to fetch news feed '%s': %s",
                    url,
                    exc,
                    exc_info=True,
                )

        logger.info(
            "News collection complete: feeds=%d total_articles=%d",
            len(feed_urls),
            len(articles),
        )
        return articles

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_feed(self, url: str) -> list[NewsArticle]:
        """Download and parse a single RSS feed URL."""
        response = await self._client.get(url)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        if feed.bozo:
            logger.warning(
                "RSS feed '%s' has parsing issues: %s",
                url,
                feed.bozo_exception,
            )
        source_name = self._extract_source_name(feed, url)

        articles: list[NewsArticle] = []
        for entry in feed.entries:
            article = self._parse_entry(entry, source_name)
            if article is not None:
                articles.append(article)

        return articles

    @staticmethod
    def _extract_source_name(feed: feedparser.FeedParserDict, url: str) -> str:
        """Extract a human-readable source name from the parsed feed or URL."""
        try:
            title: str = feed.feed.get("title", "")
            if title:
                return title
        except AttributeError:
            pass
        # Fallback: use the hostname portion of the URL
        try:
            from urllib.parse import urlparse

            return urlparse(url).hostname or url
        except Exception:  # noqa: BLE001
            return url

    @staticmethod
    def _parse_entry(
        entry: feedparser.FeedParserDict,
        source: str,
    ) -> NewsArticle | None:
        """Parse a single feedparser entry into a NewsArticle.

        Returns ``None`` if mandatory fields (title, link) are missing.
        """
        title: str = getattr(entry, "title", "").strip()
        link: str = getattr(entry, "link", "").strip()

        if not title or not link:
            logger.debug("Skipping RSS entry with missing title or link: %r", entry)
            return None

        # Content: prefer content[0].value, fall back to summary
        content: str | None = None
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "").strip() or None
        if not content:
            summary = getattr(entry, "summary", "").strip()
            content = summary or None

        # Published date
        published_at: datetime | None = None
        published_str: str = getattr(entry, "published", "").strip()
        if published_str:
            try:
                published_at = parsedate_to_datetime(published_str)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Could not parse published date '%s' for entry '%s'",
                    published_str,
                    title,
                )

        return NewsArticle(
            title=title,
            content=content,
            source=source,
            url=link,
            published_at=published_at,
            sentiment_score=None,
        )
