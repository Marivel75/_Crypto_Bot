"""Unit tests for NewsCollector — RSS feed fetching, all HTTP calls mocked."""

from __future__ import annotations

import logging

import httpx
import pytest
import respx

from src.etl.collectors.news import NewsCollector
from src.shared.models.crypto import NewsArticle

# ---------------------------------------------------------------------------
# Sample RSS fixtures
# ---------------------------------------------------------------------------

SAMPLE_RSS_VALID = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Decrypt</title>
    <link>https://decrypt.co</link>
    <item>
      <title>Bitcoin hits new high</title>
      <link>https://decrypt.co/article1</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <description>BTC surges past $100k</description>
    </item>
    <item>
      <title>Ethereum upgrade scheduled</title>
      <link>https://decrypt.co/article2</link>
      <pubDate>Tue, 02 Jan 2024 08:30:00 GMT</pubDate>
      <description>Next ETH hard fork approaching</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_MISSING_TITLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Cointelegraph</title>
    <item>
      <link>https://cointelegraph.com/article1</link>
      <description>An article without a title</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_MISSING_LINK = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Cointelegraph</title>
    <item>
      <title>Article without a link</title>
      <description>Missing link field</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_NO_ITEMS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
  </channel>
</rss>
"""

SAMPLE_RSS_INVALID_DATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BadDate Feed</title>
    <item>
      <title>Article with bad date</title>
      <link>https://example.com/article1</link>
      <pubDate>not-a-real-date</pubDate>
      <description>Content</description>
    </item>
  </channel>
</rss>
"""

_DECRYPT_URL = "https://decrypt.co/feed"
_COINTELEGRAPH_URL = "https://cointelegraph.com/rss"
_CUSTOM_URL = "https://example.com/rss"


class TestNewsCollectorFetchNews:
    """Tests for NewsCollector.fetch_news."""

    @respx.mock
    async def test_returns_articles_from_single_feed(self) -> None:
        respx.get(_CUSTOM_URL).mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_VALID, headers={"Content-Type": "application/rss+xml"})
        )

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert len(articles) == 2

    @respx.mock
    async def test_returned_objects_are_news_article_instances(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        for article in articles:
            assert isinstance(article, NewsArticle)

    @respx.mock
    async def test_article_fields_are_parsed_correctly(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        first = articles[0]
        assert first.title == "Bitcoin hits new high"
        assert first.url == "https://decrypt.co/article1"

    @respx.mock
    async def test_article_source_name_extracted_from_feed_title(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert articles[0].source == "Decrypt"

    @respx.mock
    async def test_published_date_is_parsed_to_utc_aware_datetime(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert articles[0].published_at is not None
        assert articles[0].published_at.tzinfo is not None

    @respx.mock
    async def test_article_content_from_description_fallback(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert articles[0].content == "BTC surges past $100k"

    @respx.mock
    async def test_entry_missing_title_is_skipped(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_MISSING_TITLE))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert len(articles) == 0

    @respx.mock
    async def test_entry_missing_link_is_skipped(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_MISSING_LINK))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert len(articles) == 0

    @respx.mock
    async def test_empty_feed_returns_empty_list(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_NO_ITEMS))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert articles == []

    @respx.mock
    async def test_invalid_pub_date_is_ignored_article_still_returned(self) -> None:
        """An article with an unparseable date should still be returned, with published_at=None."""
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_INVALID_DATE))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_CUSTOM_URL])

        assert len(articles) == 1
        assert articles[0].published_at is None

    @respx.mock
    async def test_multiple_feeds_are_combined(self) -> None:
        rss_b = SAMPLE_RSS_VALID.replace("Decrypt", "Cointelegraph")
        respx.get(_DECRYPT_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))
        respx.get(_COINTELEGRAPH_URL).mock(return_value=httpx.Response(200, text=rss_b))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_DECRYPT_URL, _COINTELEGRAPH_URL])

        assert len(articles) == 4

    @respx.mock
    async def test_failed_feed_is_logged_and_skipped(self, caplog: pytest.LogCaptureFixture) -> None:
        """A feed that returns an HTTP error must be skipped; other feeds still process."""
        respx.get(_DECRYPT_URL).mock(return_value=httpx.Response(503, text="unavailable"))
        respx.get(_COINTELEGRAPH_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        with caplog.at_level(logging.ERROR, logger="src.etl.collectors.news"):
            async with NewsCollector() as collector:
                articles = await collector.fetch_news(sources=[_DECRYPT_URL, _COINTELEGRAPH_URL])

        # Only Cointelegraph articles returned; Decrypt feed was skipped
        assert len(articles) == 2
        # An error was logged for the failing feed
        assert any(_DECRYPT_URL in r.message for r in caplog.records)

    @respx.mock
    async def test_network_error_on_one_feed_does_not_abort_others(self) -> None:
        respx.get(_DECRYPT_URL).mock(side_effect=httpx.ConnectError("refused"))
        respx.get(_COINTELEGRAPH_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news(sources=[_DECRYPT_URL, _COINTELEGRAPH_URL])

        assert len(articles) == 2

    @respx.mock
    async def test_uses_default_sources_when_none_provided(self) -> None:
        respx.get(_DECRYPT_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_VALID))
        respx.get(_COINTELEGRAPH_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_NO_ITEMS))

        async with NewsCollector() as collector:
            articles = await collector.fetch_news()

        # Default sources include both Decrypt and Cointelegraph
        assert len(articles) == 2


class TestNewsCollectorExtractSourceName:
    """Tests for the _extract_source_name static helper."""

    def test_extracts_title_from_feed(self) -> None:
        import feedparser

        feed = feedparser.parse(SAMPLE_RSS_VALID)
        name = NewsCollector._extract_source_name(feed, _CUSTOM_URL)
        assert name == "Decrypt"

    def test_falls_back_to_hostname_when_no_title(self) -> None:
        import feedparser

        feed = feedparser.parse(SAMPLE_RSS_NO_ITEMS.replace("<title>Empty Feed</title>", ""))
        name = NewsCollector._extract_source_name(feed, "https://example.com/rss")
        # Either hostname or URL as final fallback
        assert "example.com" in name or name == "https://example.com/rss"


class TestNewsCollectorContextManager:
    """Tests for async context manager lifecycle."""

    @respx.mock
    async def test_context_manager_closes_client(self) -> None:
        respx.get(_CUSTOM_URL).mock(return_value=httpx.Response(200, text=SAMPLE_RSS_NO_ITEMS))

        collector = NewsCollector()
        async with collector:
            await collector.fetch_news(sources=[_CUSTOM_URL])

        assert collector._client.is_closed

    async def test_close_is_idempotent(self) -> None:
        collector = NewsCollector()
        await collector.close()
        await collector.close()
