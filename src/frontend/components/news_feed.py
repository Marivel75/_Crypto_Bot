"""News feed components — article cards, sentiment chart, and word cloud."""

from __future__ import annotations

import logging
import math
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from src.frontend.components.candlestick import _DARK_LAYOUT
from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Sentiment score thresholds for label/color classification.
# Scores are expected to be in the range [−1, +1].
_SENTIMENT_POSITIVE_THRESHOLD: float = 0.3
_SENTIMENT_NEGATIVE_THRESHOLD: float = -0.3

# Sentiment color palette — accessible colors that work on dark and light bg.
_SENTIMENT_COLORS: dict[str, str] = {
    "positive": "#26c6a0",  # teal-green
    "negative": "#ef5350",  # warm red
    "neutral": "#64b5f6",  # sky blue
}

# Maximum keyword tags shown in a card before truncation
_MAX_KEYWORDS_DISPLAYED: int = 6


def _sentiment_label_and_color(score: float) -> tuple[str, str]:
    """Classify a sentiment score into a label and matching hex color.

    Args:
        score: Normalised sentiment value in [−1, +1].

    Returns:
        Tuple of (human-readable label, hex color string).
    """
    if score > _SENTIMENT_POSITIVE_THRESHOLD:
        return t("news.sentiment_positive"), _SENTIMENT_COLORS["positive"]
    if score < _SENTIMENT_NEGATIVE_THRESHOLD:
        return t("news.sentiment_negative"), _SENTIMENT_COLORS["negative"]
    return t("news.sentiment_neutral"), _SENTIMENT_COLORS["neutral"]


def render_news_card(article: dict[str, Any]) -> None:
    """Render a single news article as a styled card with sentiment indicator.

    The card layout:
    - Top row: clickable title (or plain text if no URL)
    - Second row: source + date (left), colored sentiment badge (right)
    - Bottom row: keyword tags (up to ``_MAX_KEYWORDS_DISPLAYED``)

    Handles all missing fields gracefully with sensible defaults.

    Args:
        article: Dict with optional keys title, source, sentiment_score,
            keywords, published_at, url.
    """
    title = article.get("title") or t("news.untitled")
    source = article.get("source") or t("news.unknown_source")
    sentiment = article.get("sentiment_score")
    keywords: list[Any] = article.get("keywords") or []
    published = article.get("published_at") or ""
    url = article.get("url") or ""

    with st.container(border=True):
        # --- Title row ---
        if url:
            st.markdown(f"**[{title}]({url})**")
        else:
            st.markdown(f"**{title}**")

        # --- Meta row: source/date + sentiment badge ---
        col_meta, col_sentiment = st.columns([3, 1])
        with col_meta:
            meta_parts = [p for p in [source, published] if p]
            st.caption(" · ".join(meta_parts))

        with col_sentiment:
            if sentiment is not None:
                try:
                    s = float(sentiment)
                except (TypeError, ValueError):
                    logger.warning("Invalid sentiment_score %r for article: %s", sentiment, title)
                    s = None

                if s is not None:
                    label, color = _sentiment_label_and_color(s)
                    # Inline HTML badge: colored dot + label + numeric score
                    st.markdown(
                        f'<span style="color:{color};font-size:0.78rem;font-weight:600;">● {label} ({s:+.2f})</span>',
                        unsafe_allow_html=True,
                    )

        # --- Keyword tags ---
        visible_keywords = [kw for kw in keywords[:_MAX_KEYWORDS_DISPLAYED] if kw]
        if visible_keywords:
            tags = " ".join(f"`{kw}`" for kw in visible_keywords)
            st.markdown(tags)


def render_sentiment_chart(data: list[dict[str, Any]] | None) -> go.Figure | None:
    """Build a color-coded horizontal bar chart of sentiment scores per symbol.

    Bars are colored by sentiment zone:
    - Positive (> 0.3)  → teal-green
    - Negative (< −0.3) → warm red
    - Neutral            → sky blue

    Args:
        data: List of dicts with 'symbol' and 'sentiment_score' keys.
            Returns None when data is None or empty.

    Returns:
        Plotly Figure ready for ``st.plotly_chart``, or None if no data.
    """
    if not data:
        logger.debug("render_sentiment_chart called with empty data")
        return None

    symbols: list[str] = []
    scores: list[float] = []
    for d in data:
        sym = d.get("symbol") or "?"
        raw_score = d.get("sentiment_score")
        try:
            score = float(raw_score) if raw_score is not None else 0.0
        except (TypeError, ValueError):
            logger.warning("Invalid sentiment_score %r for symbol %s", raw_score, sym)
            score = 0.0
        symbols.append(sym)
        scores.append(score)

    # Assign bar color per sentiment zone
    colors = [
        _SENTIMENT_COLORS["positive"]
        if s > _SENTIMENT_POSITIVE_THRESHOLD
        else _SENTIMENT_COLORS["negative"]
        if s < _SENTIMENT_NEGATIVE_THRESHOLD
        else _SENTIMENT_COLORS["neutral"]
        for s in scores
    ]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=symbols,
            orientation="h",
            marker_color=colors,
            marker_line_color="rgba(0,0,0,0.2)",
            marker_line_width=0.5,
            text=[f"{s:+.2f}" for s in scores],
            textposition="auto",
            textfont={"size": 11, "color": "#e0e0e0"},
            opacity=0.9,
        )
    )
    fig.update_layout(
        title={"text": t("news.chart_title"), "font": {"size": 14}},
        xaxis_title=t("news.chart_x_axis"),
        xaxis={
            "range": [-1.1, 1.1],  # fix axis to the normalised range for visual consistency
            "gridcolor": "rgba(255,255,255,0.06)",
            "zerolinecolor": "rgba(255,255,255,0.2)",
            "zerolinewidth": 1.5,
        },
        yaxis={"gridcolor": "rgba(255,255,255,0.04)"},
        height=max(280, 40 * len(symbols)),  # grow with number of symbols
        **_DARK_LAYOUT,
    )
    return fig


def render_word_cloud(keywords: list[dict[str, Any]] | None) -> go.Figure | None:
    """Approximate a word cloud with a Plotly scatter-text chart.

    Words are laid out in a square grid, with font size proportional to their
    count relative to the most-frequent word.  Colors cycle through the
    sentiment palette for visual variety.

    Args:
        keywords: List of dicts with 'word' and 'count' keys.
            Returns None when keywords is None or empty.

    Returns:
        Plotly Figure ready for ``st.plotly_chart``, or None if no data.
    """
    if not keywords:
        logger.debug("render_word_cloud called with empty keywords")
        return None

    # Filter out blank words before processing
    valid_kw = [kw for kw in keywords if kw.get("word")]
    if not valid_kw:
        return None

    words = [str(kw["word"]) for kw in valid_kw]
    counts: list[int] = []
    for kw in valid_kw:
        try:
            counts.append(max(1, int(kw.get("count", 1))))
        except (TypeError, ValueError):
            counts.append(1)

    max_count = max(counts)

    # Arrange words in a roughly square grid
    cols = max(int(math.sqrt(len(words))), 1)
    x_coords = [i % cols for i in range(len(words))]
    y_coords = [i // cols for i in range(len(words))]

    # Font size scaled between 11px (rare words) and 46px (most frequent)
    sizes = [max(11, int(46 * c / max_count)) for c in counts]

    # Cycle through accent colors for visual variety
    accent_colors = [
        _SENTIMENT_COLORS["positive"],
        _SENTIMENT_COLORS["neutral"],
        "#f9a825",  # amber accent
        "#ce93d8",  # soft purple
    ]
    word_colors = [accent_colors[i % len(accent_colors)] for i in range(len(words))]

    fig = go.Figure(
        go.Scatter(
            x=x_coords,
            y=y_coords,
            mode="text",
            text=words,
            textfont={"size": sizes, "color": word_colors},
            hovertemplate="%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title={"text": t("news.wordcloud_title"), "font": {"size": 14}},
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=320,
        **_DARK_LAYOUT,
    )
    return fig
