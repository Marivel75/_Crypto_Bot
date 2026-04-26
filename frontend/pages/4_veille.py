"""Page 4 — Veille : actualités crypto avec analyse de sentiment."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from frontend.api_client import APIClient
from frontend.components.news_feed import render_news_feed, render_sentiment_summary
from frontend.i18n import t

_client = APIClient()

# ---------------------------------------------------------------------------
# Cached data fetchers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120)
def _fetch_news(source: str | None, sentiment: str | None, limit: int) -> list[dict] | None:
    return _client.fetch_news(source=source, sentiment=sentiment, limit=limit)


@st.cache_data(ttl=300)
def _fetch_sources() -> list[str]:
    return _client.fetch_news_sources() or []


@st.cache_data(ttl=120)
def _fetch_sentiment() -> list[dict] | None:
    return _client.fetch_news_sentiment()


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.header(t("news.header"))

# Sidebar filters
with st.sidebar:
    st.markdown(f"### {t('news.filters')}")
    sources = _fetch_sources()
    source_options = [t("news.all_sources")] + sources
    selected_source = st.selectbox(t("news.source_label"), source_options)
    source_filter = None if selected_source == t("news.all_sources") else selected_source

    sentiment_options = [
        t("news.all_sentiments"),
        t("news.positive"),
        t("news.negative"),
        t("news.neutral"),
    ]
    _sentiment_map = {
        t("news.all_sentiments"): None,
        t("news.positive"): "positive",
        t("news.negative"): "negative",
        t("news.neutral"): "neutral",
    }
    selected_sentiment = st.selectbox(t("news.sentiment_label"), sentiment_options)
    sentiment_filter = _sentiment_map[selected_sentiment]

    limit = st.slider(t("news.limit"), min_value=10, max_value=200, value=50, step=10)
    st.divider()
    if st.button(t("dashboard.refresh")):
        st.cache_data.clear()

# ---------------------------------------------------------------------------
# Main content: two tabs
# ---------------------------------------------------------------------------

with st.expander(t("news.vader_title"), expanded=False):
    st.markdown(t("news.vader_explanation"))

tab_articles, tab_sentiment = st.tabs([t("news.tab_articles"), t("news.tab_sentiment")])

with tab_articles:
    with st.spinner(t("news.loading")):
        articles = _fetch_news(source_filter, sentiment_filter, limit)

    if articles is None:
        st.error(t("api.unavailable"))
        st.stop()

    if not articles:
        st.info(t("news.no_articles"))
    else:
        st.caption(t("news.article_count").format(n=len(articles)))
        render_news_feed(articles)

with tab_sentiment:
    with st.spinner(t("news.loading")):
        sentiment_data = _fetch_sentiment()

    if sentiment_data is None:
        st.error(t("api.unavailable"))
    else:
        render_sentiment_summary(sentiment_data)
