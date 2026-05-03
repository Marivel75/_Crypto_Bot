"""Collecteur synchrone d'articles de news via flux RSS.

Récupère les articles depuis les sources RSS configurées, calcule un score
de sentiment VADER (compound −1 à +1) et extrait les mots-clés de chaque article.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import feedparser  # type: ignore[import-untyped]
import httpx

from src.ml.nlp.text_mining import extract_keywords, extract_entities, detect_topics

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

DEFAULT_SOURCES: tuple[str, ...] = (
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://cryptonews.com/news/feed/",
)

# Simple English stop-word list used for keyword extraction
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "has", "have", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "that", "this", "its", "it", "his",
    "her", "their", "our", "your", "what", "which", "who", "how", "when",
    "where", "why", "not", "no", "new", "says", "said", "over", "more",
    "also", "than", "into", "about", "after", "before", "crypto", "bitcoin",
})

# VADER sentiment analyser (lazy init)
_vader = None


def _get_vader():
    global _vader
    if _vader is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader = SentimentIntensityAnalyzer()
        except ImportError:
            logger.warning("vaderSentiment not installed — sentiment scoring disabled")
    return _vader


def _analyse_sentiment(text: str) -> tuple[float | None, str | None]:
    """Return (compound_score, label) for the given text using VADER.

    compound ∈ [−1, +1]; label is 'positive', 'negative', or 'neutral'.
    Returns (None, None) when VADER is unavailable.
    """
    vader = _get_vader()
    if vader is None or not text:
        return None, None
    scores = vader.polarity_scores(text[:500])
    compound = round(scores["compound"], 4)
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return compound, label


def _extract_keywords(title: str, content: str | None, max_kw: int = 6) -> list[str]:
    """Return the top *max_kw* meaningful tokens from title + content."""
    text = f"{title} {content or ''}".lower()
    tokens = re.findall(r"\b[a-zA-Z]{4,}\b", text)
    seen: set[str] = set()
    keywords: list[str] = []
    for tok in tokens:
        if tok not in _STOPWORDS and tok not in seen:
            seen.add(tok)
            keywords.append(tok)
            if len(keywords) >= max_kw:
                break
    return keywords


@dataclass
class ArticleData:
    """Intermediate dataclass for a parsed RSS entry (before DB storage)."""
    title: str
    url: str
    source: str
    content: str | None = None
    published_at: datetime | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    keywords: list[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)


class NewsCollector:
    """Synchronous RSS news collector.

    Fetches raw RSS XML over HTTP (httpx), parses with feedparser,
    scores sentiment with VADER, and extracts keywords.
    """

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": "crypto-bot/1.0 (RSS reader)"},
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NewsCollector:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_articles(self, sources: list[str] | None = None) -> list[ArticleData]:
        """Fetch and parse RSS feeds into ArticleData objects.

        Args:
            sources: RSS feed URLs to fetch. Defaults to DEFAULT_SOURCES.

        Returns:
            Combined list of ArticleData from all sources.
            Failed feeds are logged and skipped.
        """
        feed_urls = sources if sources is not None else list(DEFAULT_SOURCES)
        articles: list[ArticleData] = []

        for url in feed_urls:
            try:
                feed_articles = self._fetch_feed(url)
                articles.extend(feed_articles)
                logger.info("feed=%s articles=%d", url, len(feed_articles))
            except Exception as exc:
                logger.error("Failed to fetch feed '%s': %s", url, exc, exc_info=True)

        logger.info("Collection done: feeds=%d total=%d", len(feed_urls), len(articles))
        return articles

    def fetch_and_store(
        self,
        db,
        sources: list[str] | None = None,
    ) -> dict[str, int]:
        """Fetch articles and persist new ones to the database.

        Args:
            db: SQLAlchemy Session.
            sources: RSS feed URLs (defaults to DEFAULT_SOURCES).

        Returns:
            Dict with 'stored' and 'skipped' counts.
        """
        from src.models.news import NewsArticle

        articles = self.fetch_articles(sources)
        stored = skipped = 0

        for art in articles:
            exists = db.query(NewsArticle).filter(NewsArticle.url == art.url).first()
            if exists:
                skipped += 1
                continue
            db.add(NewsArticle(
                id=str(uuid.uuid4()),
                title=art.title,
                url=art.url,
                source=art.source,
                content=art.content,
                published_at=art.published_at,
                sentiment_score=art.sentiment_score,
                sentiment_label=art.sentiment_label,
                keywords=art.keywords,
                entities=art.entities,
                topics=art.topics,
            ))
            stored += 1

        db.commit()
        logger.info("Stored %d articles, skipped %d duplicates", stored, skipped)
        return {"stored": stored, "skipped": skipped}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_feed(self, url: str) -> list[ArticleData]:
        response = self._client.get(url)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        if feed.bozo:
            logger.warning("Feed '%s' has parse issues: %s", url, feed.bozo_exception)

        source_name = self._extract_source_name(feed, url)
        return [
            article
            for entry in feed.entries
            if (article := self._parse_entry(entry, source_name)) is not None
        ]

    @staticmethod
    def _extract_source_name(feed: Any, url: str) -> str:
        try:
            title = feed.feed.get("title", "")
            if title:
                return title
        except AttributeError:
            pass
        try:
            return urlparse(url).hostname or url
        except Exception:
            return url

    @staticmethod
    def _parse_entry(entry: Any, source: str) -> ArticleData | None:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
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
        published_str = getattr(entry, "published", "").strip()
        if published_str:
            try:
                published_at = parsedate_to_datetime(published_str)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                logger.debug("Could not parse date '%s' for '%s'", published_str, title)

        full_text = f"{title} {content or ''}"
        sentiment_score, sentiment_label = _analyse_sentiment(full_text)
        keywords = extract_keywords(full_text, top_n=8)
        entities = extract_entities(full_text)
        topics = detect_topics(full_text)

        return ArticleData(
            title=title,
            url=link,
            source=source,
            content=content,
            published_at=published_at,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            keywords=keywords,
            entities=entities,
            topics=topics,
        )
