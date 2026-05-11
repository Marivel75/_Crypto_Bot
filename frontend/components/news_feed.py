"""Streamlit component for displaying news articles with sentiment."""

from __future__ import annotations

import re
import streamlit as st

from frontend.i18n import t

_LABEL_COLORS = {
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral":  "#94a3b8",
}

_TOPIC_COLORS = {
    "regulation":    "#a78bfa",
    "hack_security": "#ef4444",
    "adoption":      "#22c55e",
    "defi":          "#38bdf8",
    "nft":           "#f472b6",
    "macro":         "#fb923c",
    "price_action":  "#fbbf24",
    "general":       "#475569",
}

_LABEL_ICONS = {
    "positive": "▲",
    "negative": "▼",
    "neutral":  "●",
}

_RE_HTML = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _RE_HTML.sub(" ", text).strip()


def render_news_feed(articles: list[dict]) -> None:
    """Render a list of news article dicts as a Streamlit feed."""
    if not articles:
        st.info(t("news.no_articles"))
        return

    for art in articles:
        title = art.get("title", "—")
        url = art.get("url", "")
        source = art.get("source", "—")
        published_at = art.get("published_at") or art.get("collected_at") or ""
        if published_at and "T" in str(published_at):
            published_at = str(published_at)[:16].replace("T", " ")
        elif published_at:
            published_at = str(published_at)[:16]

        sentiment_label = art.get("sentiment_label")
        sentiment_score = art.get("sentiment_score")
        keywords: list[str] = art.get("keywords") or []

        # Strip HTML from content before preview so no link is duplicated
        content_raw = art.get("content") or ""
        content_clean = _strip_html(content_raw)
        content_preview = content_clean[:200].strip() + ("…" if len(content_clean) > 200 else "")

        topics: list[str] = art.get("topics") or []
        entities: dict = art.get("entities") or {}
        crypto_symbols: list[str] = entities.get("crypto_symbols") or []

        # Badge HTML (no links, safe for st.html)
        color = _LABEL_COLORS.get(sentiment_label or "neutral", "#94a3b8")
        icon = _LABEL_ICONS.get(sentiment_label or "neutral", "●")
        score_str = f" {sentiment_score:+.2f}" if sentiment_score is not None else ""
        badge_html = (
            f'<span style="color:{color};font-weight:600">'
            f'{icon} {sentiment_label or "—"}{score_str}</span>'
        )

        # Tag spans (no links)
        topic_spans = " ".join(
            f'<span style="background:{_TOPIC_COLORS.get(topic, "#475569")}22;'
            f'color:{_TOPIC_COLORS.get(topic, "#475569")};'
            f'border:1px solid {_TOPIC_COLORS.get(topic, "#475569")}55;'
            f'padding:1px 7px;border-radius:10px;font-size:0.75em;font-weight:600">'
            f'{topic.replace("_", " ")}</span>'
            for topic in topics if topic != "general"
        )
        symbol_spans = " ".join(
            f'<span style="background:#0ea5e922;color:#38bdf8;'
            f'border:1px solid #0ea5e955;padding:1px 6px;border-radius:4px;font-size:0.75em;font-weight:700">'
            f'{sym}</span>'
            for sym in crypto_symbols[:4]
        )
        kw_spans = " ".join(
            f'<span style="background:#1e293b;color:#94a3b8;'
            f'padding:1px 6px;border-radius:4px;font-size:0.78em">{kw}</span>'
            for kw in keywords[:5]
        )
        tags_combined = " ".join(filter(None, [topic_spans, symbol_spans]))

        with st.container(border=True):
            # Header: source · date · sentiment (st.html for colors, no title text here)
            st.html(
                f'<div style="font-size:0.8em;color:#8b949e;margin-bottom:2px">'
                f'{source} &nbsp;·&nbsp; {published_at} &nbsp;·&nbsp; {badge_html}'
                f'</div>'
            )
            # Title as native markdown link — pas de <a href> dans st.html
            safe_title = title.replace("[", "\\[").replace("]", "\\]")
            if url:
                st.markdown(f"**[{safe_title}]({url})**")
            else:
                st.markdown(f"**{safe_title}**")
            # Content preview as plain text (HTML stripped)
            if content_preview:
                st.caption(content_preview)
            # Tags (st.html safe: no links, no title text)
            if tags_combined or kw_spans:
                all_tags = " ".join(filter(None, [tags_combined, kw_spans]))
                st.html(f'<div style="margin-top:2px">{all_tags}</div>')


def render_sentiment_summary(sentiment_data: list[dict]) -> None:
    """Render a per-source sentiment summary as a compact table."""
    if not sentiment_data:
        st.info(t("news.no_sentiment"))
        return

    st.markdown(f"#### {t('news.sentiment_by_source')}")
    cols = st.columns([3, 1, 1, 1, 1, 2])
    cols[0].markdown("**Source**")
    cols[1].markdown("**Total**")
    cols[2].markdown(f"**{t('news.positive')}**")
    cols[3].markdown(f"**{t('news.negative')}**")
    cols[4].markdown(f"**{t('news.neutral')}**")
    cols[5].markdown(f"**{t('news.avg_score')}**")

    for row in sentiment_data:
        cols = st.columns([3, 1, 1, 1, 1, 2])
        cols[0].write(row.get("source", "—"))
        cols[1].write(row.get("total", 0))
        pos = row.get("positive", 0)
        neg = row.get("negative", 0)
        neu = row.get("neutral", 0)
        cols[2].markdown(f'<span style="color:#22c55e">{pos}</span>', unsafe_allow_html=True)
        cols[3].markdown(f'<span style="color:#ef4444">{neg}</span>', unsafe_allow_html=True)
        cols[4].markdown(f'<span style="color:#94a3b8">{neu}</span>', unsafe_allow_html=True)
        avg = row.get("avg_score")
        if avg is not None:
            color = "#22c55e" if avg > 0.05 else "#ef4444" if avg < -0.05 else "#94a3b8"
            cols[5].markdown(f'<span style="color:{color}">{avg:+.3f}</span>', unsafe_allow_html=True)
        else:
            cols[5].write("—")
