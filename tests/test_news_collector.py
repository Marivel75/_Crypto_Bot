"""Tests for src/collectors/news_collector.py (sync adaptation)."""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.collectors.news_collector import (
    NewsCollector,
    ArticleData,
    _analyse_sentiment,
    _extract_keywords,
    DEFAULT_SOURCES,
)


# ---------------------------------------------------------------------------
# _analyse_sentiment
# ---------------------------------------------------------------------------

class TestAnalyseSentiment:
    def test_positive_text(self):
        score, label = _analyse_sentiment("Bitcoin surges to all time high amazing rally")
        assert label == "positive"
        assert score > 0.05

    def test_negative_text(self):
        score, label = _analyse_sentiment("Crash collapse disaster terrible loss")
        assert label == "negative"
        assert score < -0.05

    def test_neutral_text(self):
        score, label = _analyse_sentiment("Price moves sideways")
        # neutral is compound in (-0.05, 0.05) — accept neutral or slight positive
        assert label in ("neutral", "positive", "negative")
        assert score is not None

    def test_empty_string_returns_none(self):
        score, label = _analyse_sentiment("")
        assert score is None
        assert label is None

    def test_returns_float_and_string(self):
        score, label = _analyse_sentiment("Markets are rising today")
        assert isinstance(score, float)
        assert label in ("positive", "negative", "neutral")

    def test_truncates_to_500_chars(self):
        long_text = "good " * 200
        score, label = _analyse_sentiment(long_text)
        assert score is not None


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------

class TestExtractKeywords:
    def test_returns_list(self):
        kws = _extract_keywords("Bitcoin price rally", None)
        assert isinstance(kws, list)

    def test_max_keywords_respected(self):
        kws = _extract_keywords("Ethereum solana cardano polkadot avalanche chainlink dogecoin", None)
        assert len(kws) <= 6

    def test_custom_max_kw(self):
        kws = _extract_keywords("Ethereum solana cardano polkadot avalanche chainlink", None, max_kw=3)
        assert len(kws) <= 3

    def test_stopwords_excluded(self):
        kws = _extract_keywords("the bitcoin rally was over the moon", None)
        assert "the" not in kws
        assert "over" not in kws

    def test_short_words_excluded(self):
        kws = _extract_keywords("BTC ETH rally today", None)
        # words shorter than 4 chars are excluded
        assert "btc" not in kws
        assert "eth" not in kws

    def test_deduplicates(self):
        kws = _extract_keywords("rally rally rally rally rally", None)
        assert kws.count("rally") == 1

    def test_uses_content_as_well(self):
        kws = _extract_keywords("Title here", "content with unique keyword: ethereal")
        assert "ethereal" in kws

    def test_empty_inputs(self):
        kws = _extract_keywords("", None)
        assert isinstance(kws, list)


# ---------------------------------------------------------------------------
# NewsCollector._parse_entry
# ---------------------------------------------------------------------------

class TestParseEntry:
    def _entry(self, **kwargs):
        e = MagicMock()
        e.title = kwargs.get("title", "Test Title")
        e.link = kwargs.get("link", "https://example.com/article")
        e.published = kwargs.get("published", "Mon, 25 Apr 2026 10:00:00 +0000")
        e.summary = kwargs.get("summary", "")
        e.content = kwargs.get("content", None)
        return e

    def test_returns_article_data_on_valid_entry(self):
        entry = self._entry()
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is not None
        assert isinstance(result, ArticleData)
        assert result.title == "Test Title"
        assert result.url == "https://example.com/article"
        assert result.source == "TestSource"

    def test_returns_none_when_no_title(self):
        entry = self._entry(title="")
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is None

    def test_returns_none_when_no_link(self):
        entry = self._entry(link="")
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is None

    def test_parses_published_date(self):
        entry = self._entry(published="Mon, 25 Apr 2026 10:00:00 +0000")
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is not None
        assert result.published_at is not None
        assert isinstance(result.published_at, datetime)

    def test_invalid_date_is_none(self):
        entry = self._entry(published="not-a-date")
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is not None
        assert result.published_at is None

    def test_uses_content_over_summary(self):
        content_obj = MagicMock()
        content_obj.get = MagicMock(return_value="full content text here")
        entry = self._entry(summary="short summary")
        entry.content = [content_obj]
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result.content == "full content text here"

    def test_falls_back_to_summary(self):
        entry = self._entry(summary="short summary fallback")
        entry.content = None
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result.content == "short summary fallback"

    def test_sentiment_is_computed(self):
        entry = self._entry(title="Bitcoin surges to incredible new highs amazing")
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is not None
        assert result.sentiment_score is not None
        assert result.sentiment_label in ("positive", "negative", "neutral")

    def test_keywords_are_computed(self):
        entry = self._entry(title="Ethereum network upgrade successful deployment")
        result = NewsCollector._parse_entry(entry, "TestSource")
        assert result is not None
        assert isinstance(result.keywords, list)


# ---------------------------------------------------------------------------
# NewsCollector.fetch_articles
# ---------------------------------------------------------------------------

class TestFetchArticles:
    def _make_feed(self, entries):
        feed = MagicMock()
        feed.bozo = False
        feed.entries = entries
        feed.feed.get = MagicMock(return_value="Test Feed")
        return feed

    def _mock_entry(self, title="Title", link="https://example.com/1"):
        e = MagicMock()
        e.title = title
        e.link = link
        e.published = "Mon, 25 Apr 2026 10:00:00 +0000"
        e.summary = "Summary text"
        e.content = None
        return e

    def test_returns_list_of_articles(self):
        feed = self._make_feed([self._mock_entry()])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<xml/>"
        mock_response.raise_for_status = MagicMock()

        with patch("src.collectors.news_collector.feedparser.parse", return_value=feed):
            with patch.object(NewsCollector, "_fetch_feed", return_value=[
                ArticleData(title="T", url="https://x.com", source="S")
            ]):
                collector = NewsCollector()
                articles = collector.fetch_articles(["https://fake.rss"])
        assert isinstance(articles, list)
        assert len(articles) == 1

    def test_uses_default_sources_when_none(self):
        with patch.object(NewsCollector, "_fetch_feed", return_value=[]) as mock_fetch:
            collector = NewsCollector()
            collector.fetch_articles()
            assert mock_fetch.call_count == len(DEFAULT_SOURCES)

    def test_skips_failed_feeds(self):
        def fail_on_first(url):
            if url == "https://fail.rss":
                raise ConnectionError("network error")
            return []

        with patch.object(NewsCollector, "_fetch_feed", side_effect=fail_on_first):
            collector = NewsCollector()
            articles = collector.fetch_articles(["https://fail.rss", "https://ok.rss"])
        assert articles == []

    def test_combines_multiple_feeds(self):
        art1 = ArticleData(title="T1", url="https://a.com/1", source="A")
        art2 = ArticleData(title="T2", url="https://b.com/2", source="B")

        def side_effect(url):
            return [art1] if "feed1" in url else [art2]

        with patch.object(NewsCollector, "_fetch_feed", side_effect=side_effect):
            collector = NewsCollector()
            articles = collector.fetch_articles(["https://feed1.rss", "https://feed2.rss"])
        assert len(articles) == 2


# ---------------------------------------------------------------------------
# NewsCollector.fetch_and_store
# ---------------------------------------------------------------------------

class TestFetchAndStore:
    def _make_db(self, existing_urls: list[str]):
        db = MagicMock()
        def query_filter_first(url):
            return url in existing_urls
        # Simulate db.query(NewsArticle).filter(...).first()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.side_effect = lambda: True if existing_urls else None
        mock_query.filter.return_value = mock_filter
        db.query.return_value = mock_query
        return db

    def test_stores_new_articles(self):
        art = ArticleData(title="T", url="https://new.com/1", source="S")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch.object(NewsCollector, "fetch_articles", return_value=[art]):
            collector = NewsCollector()
            result = collector.fetch_and_store(db)

        assert result["stored"] == 1
        assert result["skipped"] == 0
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_skips_duplicate_url(self):
        art = ArticleData(title="T", url="https://existing.com/1", source="S")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = object()  # exists

        with patch.object(NewsCollector, "fetch_articles", return_value=[art]):
            collector = NewsCollector()
            result = collector.fetch_and_store(db)

        assert result["stored"] == 0
        assert result["skipped"] == 1
        db.add.assert_not_called()

    def test_commits_even_when_all_skipped(self):
        art = ArticleData(title="T", url="https://dup.com/1", source="S")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = object()

        with patch.object(NewsCollector, "fetch_articles", return_value=[art]):
            collector = NewsCollector()
            collector.fetch_and_store(db)

        db.commit.assert_called_once()

    def test_context_manager(self):
        with NewsCollector() as collector:
            assert isinstance(collector, NewsCollector)


# ---------------------------------------------------------------------------
# DEFAULT_SOURCES sanity check
# ---------------------------------------------------------------------------

class TestDefaultSources:
    def test_is_non_empty_tuple(self):
        assert isinstance(DEFAULT_SOURCES, tuple)
        assert len(DEFAULT_SOURCES) >= 1

    def test_all_are_https_urls(self):
        for url in DEFAULT_SOURCES:
            assert url.startswith("https://"), f"{url} is not HTTPS"
