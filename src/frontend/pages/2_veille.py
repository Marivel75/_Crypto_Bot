"""Page 2 — Veille & News (Sarah, Journaliste).

Filters (source, keyword, date range) -> news list + sentiment chart + word cloud.
"""

from __future__ import annotations

import logging
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.components.news_feed import (
    render_news_card,
    render_sentiment_chart,
    render_word_cloud,
)
from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Available news sources (first entry is the "all" placeholder — translated at render time)
_SOURCES_RAW = ["Decrypt", "Cointelegraph.com News", "News - Cryptonews"]


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=120)
def _fetch_news(source: str | None, keyword: str | None) -> list[dict[str, Any]] | None:
    return _get_client().fetch_news(source=source, keyword=keyword, limit=50)


@st.cache_data(ttl=120)
def _fetch_sentiment() -> list[dict[str, Any]] | None:
    return _get_client().fetch_news_sentiment()


def _aggregate_sentiment_from_articles(
    news: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group articles by source and compute average sentiment score."""
    acc: dict[str, list[float]] = defaultdict(list)
    for article in news:
        source = article.get("source", "Inconnu")
        score = article.get("sentiment_score")
        if score is not None:
            acc[source].append(float(score))

    return [{"source": src, "sentiment_score": sum(scores) / len(scores)} for src, scores in acc.items() if scores]


def _aggregate_keywords(news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Count keyword occurrences across all articles."""
    counter: Counter[str] = Counter()
    for article in news:
        for kw in article.get("keywords", []):
            counter[kw] += 1

    return [{"word": word, "count": count} for word, count in counter.most_common(30)]


def _apply_date_filter(
    news: list[dict[str, Any]],
    date_from: date,
    date_to: date,
) -> list[dict[str, Any]]:
    """Return only articles whose publication date falls within [date_from, date_to].

    Articles with a missing or unparseable date are kept to avoid silent data loss.
    """
    filtered: list[dict[str, Any]] = []
    for article in news:
        pub = article.get("published_at", "")
        if pub:
            try:
                pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00")).date()
                if date_from <= pub_date <= date_to:
                    filtered.append(article)
            except (ValueError, TypeError):
                # Keep the article when the date cannot be parsed
                filtered.append(article)
        else:
            filtered.append(article)
    return filtered


def _render_filter_bar() -> tuple[str | None, str | None, date, date]:
    """Render the filter bar and return the active filter values.

    Returns:
        Tuple of (source_filter, keyword_filter, date_from, date_to).
    """
    with st.container(border=True):
        # Row 1: source + keyword (wider inputs)
        col_source, col_keyword = st.columns([1, 2])
        with col_source:
            all_label = t("veille.all_sources")
            sources = [all_label, *_SOURCES_RAW]
            source = st.selectbox(
                t("veille.source"),
                sources,
                index=0,
                help=t("veille.source_help"),
            )
        with col_keyword:
            keyword = st.text_input(
                t("veille.keyword"),
                placeholder=t("veille.keyword_placeholder"),
                help=t("veille.keyword_help"),
            )

        # Row 2: date range with explicit labels for clarity
        col_date_from, col_date_to, col_spacer = st.columns([1, 1, 2])
        with col_date_from:
            date_from: date = st.date_input(
                t("veille.date_from"),
                value=date.today() - timedelta(days=7),
                max_value=date.today(),
                key="veille_date_from",
                help=t("veille.date_from_help"),
            )
        with col_date_to:
            date_to: date = st.date_input(
                t("veille.date_to"),
                value=date.today(),
                min_value=date_from,
                max_value=date.today(),
                key="veille_date_to",
                help=t("veille.date_to_help"),
            )

    source_filter = None if source == all_label else source
    keyword_filter = keyword.strip() or None
    return source_filter, keyword_filter, date_from, date_to


def _render_empty_state(active_filters: bool) -> None:
    """Render a styled empty-state card when no articles match the current filters."""
    hint = t("veille.no_article_filter_hint") if active_filters else t("veille.no_article_empty_hint")
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="text-align: center; padding: 2rem 1rem;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;"><i data-lucide="newspaper" style="width:2rem;height:2rem;"></i></div>
                <h4 style="margin: 0 0 0.5rem 0;">{t("veille.no_article_title")}</h4>
                <p style="opacity: 0.65; margin: 0;">
                    {hint}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_news_list(news: list[dict[str, Any]], active_filters: bool) -> None:
    """Render the left column: article list or empty state, plus CSV export."""
    st.subheader(t("veille.latest_news"))

    if not news:
        _render_empty_state(active_filters)
        return

    # Article count badge
    st.caption(t("veille.articles_found", count=len(news)))

    # Scrollable news card list
    with st.container(border=True):
        for article in news:
            render_news_card(article)

    # CSV export — placed below the card list
    st.markdown("---")
    df = pd.DataFrame(
        [
            {
                t("veille.col_title"): a.get("title", ""),
                t("veille.col_source"): a.get("source", ""),
                t("veille.col_sentiment"): a.get("sentiment_score", ""),
                t("veille.col_date"): a.get("published_at", ""),
                t("veille.col_url"): a.get("url", ""),
            }
            for a in news
        ]
    )
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=t("veille.export_csv"),
        data=csv_data,
        file_name="veille_crypto.csv",
        mime="text/csv",
        help=t("veille.export_csv_help"),
        use_container_width=True,
    )


def _render_charts_column(news: list[dict[str, Any]] | None) -> None:
    """Render the right column: sentiment bar chart and keyword word cloud."""
    # --- Sentiment chart ---
    st.subheader(t("veille.sentiment_by_source"))

    # Prefer the dedicated API endpoint; fall back to per-article aggregation
    sentiment_data = _fetch_sentiment()
    if not sentiment_data and news:
        sentiment_data = _aggregate_sentiment_from_articles(news)

    if sentiment_data:
        fig = render_sentiment_chart(sentiment_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(t("veille.sentiment_unavailable"))
    else:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center;padding:1.5rem;opacity:0.6;'>"
                f"<i data-lucide='trending-up' style='width:1.2rem;height:1.2rem;vertical-align:middle;'></i> {t('veille.no_sentiment_data')}"
                "</div>",
                unsafe_allow_html=True,
            )

    # --- Word cloud ---
    st.subheader(t("veille.trending_keywords"))

    if news:
        keywords_agg = _aggregate_keywords(news)
        fig_wc = render_word_cloud(keywords_agg)
        if fig_wc:
            st.plotly_chart(fig_wc, use_container_width=True)
        else:
            st.info(t("veille.no_keywords"))
    else:
        with st.container(border=True):
            st.markdown(
                f"<div style='text-align:center;padding:1.5rem;opacity:0.6;'><i data-lucide='file-text' style='width:1.2rem;height:1.2rem;vertical-align:middle;'></i> {t('veille.no_data')}</div>",
                unsafe_allow_html=True,
            )


def page() -> None:
    """Render the veille (news monitoring) page."""
    st.header(t("veille.header"))
    st.caption(t("veille.subtitle"))

    # --- Filter bar ---
    source_filter, keyword_filter, date_from, date_to = _render_filter_bar()

    # Determine whether any non-default filter is active (used for empty-state copy)
    default_from = date.today() - timedelta(days=7)
    default_to = date.today()
    date_changed = date_from != default_from or date_to != default_to
    active_filters = bool(source_filter or keyword_filter or date_changed)

    # --- Fetch and filter data ---
    news = _fetch_news(source_filter, keyword_filter)

    if news is None:
        # Hard API failure: surface a clear error and stop rendering
        st.error(
            t("veille.api_unavailable"),
            icon=":material/cancel:",
        )
        return

    # Apply client-side date filter
    news = _apply_date_filter(news, date_from, date_to)

    # --- Two-column layout: news feed (left) + charts (right) ---
    col_list, col_charts = st.columns([2, 1])

    with col_list:
        _render_news_list(news, active_filters)

    with col_charts:
        # Pass None when news list is empty so charts show their own empty state
        _render_charts_column(news if news else None)


page()
