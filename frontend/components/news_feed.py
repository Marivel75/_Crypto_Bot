"""Streamlit component for displaying news articles with sentiment."""

from __future__ import annotations

import streamlit as st

from frontend.i18n import t

_LABEL_COLORS = {
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral": "#94a3b8",
}

_LABEL_ICONS = {
    "positive": "▲",
    "negative": "▼",
    "neutral": "●",
}


def _sentiment_badge(label: str | None, score: float | None) -> str:
    color = _LABEL_COLORS.get(label or "neutral", "#94a3b8")
    icon = _LABEL_ICONS.get(label or "neutral", "●")
    score_str = f" {score:+.2f}" if score is not None else ""
    return f'<span style="color:{color};font-weight:600">{icon} {label or "—"}{score_str}</span>'


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
        # Format timestamp: keep only date+hour if intraday
        if published_at and "T" in str(published_at):
            published_at = str(published_at)[:16].replace("T", " ")
        elif published_at:
            published_at = str(published_at)[:16]

        sentiment_label = art.get("sentiment_label")
        sentiment_score = art.get("sentiment_score")
        keywords: list[str] = art.get("keywords") or []
        content = art.get("content") or ""
        content_preview = content[:200].strip() + ("…" if len(content) > 200 else "")

        badge = _sentiment_badge(sentiment_label, sentiment_score)
        kw_html = " ".join(
            f'<span style="background:#1e293b;color:#94a3b8;padding:1px 6px;border-radius:4px;font-size:0.78em">{kw}</span>'
            for kw in keywords[:5]
        )

        st.markdown(
            f"""
<div style="border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin-bottom:10px">
  <div style="font-size:0.8em;color:#8b949e;margin-bottom:4px">{source} &nbsp;·&nbsp; {published_at} &nbsp;·&nbsp; {badge}</div>
  <div style="font-size:1.0em;font-weight:600;margin-bottom:4px">
    {'<a href="' + url + '" target="_blank" style="color:inherit;text-decoration:none">' + title + '</a>' if url else title}
  </div>
  {('<div style="font-size:0.85em;color:#8b949e;margin-bottom:6px">' + content_preview + '</div>') if content_preview else ''}
  {('<div style="margin-top:4px">' + kw_html + '</div>') if kw_html else ''}
</div>
""",
            unsafe_allow_html=True,
        )


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
