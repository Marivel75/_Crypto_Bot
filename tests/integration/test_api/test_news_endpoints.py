"""Integration tests for news endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.orm import NewsArticleOrm

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seed_news(db_session: AsyncSession) -> list[NewsArticleOrm]:
    """Insert sample news articles and return them."""
    articles: list[NewsArticleOrm] = []
    sources = ["decrypt", "cointelegraph", "decrypt"]
    sentiments = [0.8, -0.3, 0.5]

    for i in range(3):
        article = NewsArticleOrm(
            title=f"Bitcoin news article {i}",
            content=f"Detailed content for article {i} covering BTC market movements.",
            source=sources[i],
            url=f"https://example.com/article-{i}",
            published_at=datetime(2025, 1, 1, i, tzinfo=UTC),
            sentiment_score=sentiments[i],
            keywords=["bitcoin", "crypto"],
            reliability_score=0.9,
        )
        db_session.add(article)
        articles.append(article)

    await db_session.commit()
    for a in articles:
        await db_session.refresh(a)
    return articles


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNewsEndpoints:
    # --- /latest ---

    @pytest.mark.asyncio
    async def test_get_latest_news_empty(self, client: AsyncClient) -> None:
        """GET /latest returns an empty list when no articles exist."""
        resp = await client.get("/api/v1/news/latest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["error"] is None
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_latest_news_with_data(self, client: AsyncClient) -> None:
        """GET /latest returns all seeded articles with expected fields."""
        resp = await client.get("/api/v1/news/latest")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert len(data) == 3
        assert body["meta"]["total"] == 3

        first = data[0]
        assert "id" in first
        assert "title" in first
        assert "source" in first
        assert "url" in first

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_latest_news_pagination(self, client: AsyncClient) -> None:
        """GET /latest?limit=2&page=1 returns at most 2 articles."""
        resp = await client.get("/api/v1/news/latest?limit=2&page=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 3
        assert body["meta"]["limit"] == 2
        assert body["meta"]["page"] == 1

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_latest_news_page_two(self, client: AsyncClient) -> None:
        """GET /latest?limit=2&page=2 returns the remaining article."""
        resp = await client.get("/api/v1/news/latest?limit=2&page=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["meta"]["page"] == 2

    # --- /latest?source= ---

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_news_filtered_by_source(self, client: AsyncClient) -> None:
        """GET /latest?source=decrypt returns only decrypt articles."""
        resp = await client.get("/api/v1/news/latest?source=decrypt")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        assert all(a["source"] == "decrypt" for a in data)

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_news_filtered_by_source_no_match(self, client: AsyncClient) -> None:
        """GET /latest?source=unknown returns empty list for unknown source."""
        resp = await client.get("/api/v1/news/latest?source=unknown_source")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_news_filtered_by_keyword(self, client: AsyncClient) -> None:
        """GET /latest?keyword=bitcoin matches articles whose title contains the keyword."""
        resp = await client.get("/api/v1/news/latest?keyword=bitcoin")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        assert all("bitcoin" in a["title"].lower() for a in data)

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_news_filtered_by_keyword_no_match(self, client: AsyncClient) -> None:
        """GET /latest?keyword=xyz returns empty list when keyword not found."""
        resp = await client.get("/api/v1/news/latest?keyword=xyznotfound")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    # --- /{news_id} ---

    @pytest.mark.asyncio
    async def test_get_news_by_id(
        self,
        client: AsyncClient,
        seed_news: list[NewsArticleOrm],
    ) -> None:
        """GET /{news_id} returns a single article by its ID."""
        article = seed_news[0]
        resp = await client.get(f"/api/v1/news/{article.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == str(article.id)
        assert data["title"] == article.title
        assert data["source"] == article.source

    @pytest.mark.asyncio
    async def test_get_news_by_id_not_found(self, client: AsyncClient) -> None:
        """GET /{news_id} returns 404 for an unknown ID."""
        unknown_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/news/{unknown_id}")
        assert resp.status_code == 404

    # --- /sentiment ---

    @pytest.mark.asyncio
    async def test_get_news_sentiment_empty(self, client: AsyncClient) -> None:
        """GET /sentiment returns empty list when no articles have sentiment scores."""
        resp = await client.get("/api/v1/news/sentiment")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_news_sentiment(self, client: AsyncClient) -> None:
        """GET /sentiment returns aggregate sentiment grouped by source."""
        resp = await client.get("/api/v1/news/sentiment")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0

        # Each entry must have required fields
        for entry in data:
            assert "symbol" in entry  # mapped from source in the service
            assert "sentiment_score" in entry
            assert "article_count" in entry
            assert entry["article_count"] > 0

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_news")
    async def test_get_news_sentiment_decrypt_avg(self, client: AsyncClient) -> None:
        """Decrypt average sentiment is the mean of its two seeded articles (0.8 + 0.5) / 2 = 0.65."""
        resp = await client.get("/api/v1/news/sentiment")
        assert resp.status_code == 200
        data = resp.json()["data"]

        decrypt_entry = next((e for e in data if e["symbol"] == "decrypt"), None)
        assert decrypt_entry is not None
        assert decrypt_entry["article_count"] == 2
        # sentiment_score should be close to 0.65 (rounded to 4 dp)
        assert abs(decrypt_entry["sentiment_score"] - 0.65) < 0.01
