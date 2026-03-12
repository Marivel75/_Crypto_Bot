"""Page 4 — Analytics & Heatmap.

Market heatmap (24h/7d/30d performance), Fear & Greed, market cap, correlation matrix.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.components.candlestick import _DARK_LAYOUT
from src.frontend.components.regime_badge import render_regime_badge
from src.frontend.i18n import t

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


# Symbols used for the correlation matrix
_CORRELATION_SYMBOLS: tuple[str, ...] = ("BTC", "ETH", "BNB", "SOL", "ADA")


@st.cache_data(ttl=60)
def _fetch_market() -> dict[str, Any] | None:
    """Fetch global market overview from the API."""
    return _get_client().fetch_market_overview()


@st.cache_data(ttl=60)
def _fetch_ohlcv_for_symbol(symbol: str) -> list[dict[str, Any]] | None:
    """Fetch 90 daily OHLCV candles for a single symbol."""
    return _get_client().fetch_ohlcv(symbol, "1D", limit=90)


@st.cache_data(ttl=300)
def _fetch_system_metrics() -> dict[str, Any] | None:
    """Fetch system metrics including market regime and volatility data."""
    return _get_client().fetch_system_metrics()


def _fear_greed_label(value: int) -> str:
    """Return a human-readable sentiment label for a Fear & Greed index value."""
    if value <= 25:
        return t("analytics.fg_extreme_fear")
    if value <= 45:
        return t("analytics.fg_fear")
    if value <= 55:
        return t("analytics.fg_neutral")
    if value <= 75:
        return t("analytics.fg_greed")
    return t("analytics.fg_extreme_greed")


def _fear_greed_color(value: int) -> str:
    """Return a hex colour matching the sentiment zone for the given value."""
    if value <= 25:
        return "#ef5350"
    if value <= 45:
        return "#ff9800"
    if value <= 55:
        return "#ffeb3b"
    if value <= 75:
        return "#66bb6a"
    return "#26a69a"


def _parse_fear_greed(raw: Any) -> int | None:
    """Safely parse a Fear & Greed raw value (dict or scalar) into an int."""
    if raw is None:
        return None
    try:
        return int(raw.get("value", 0)) if isinstance(raw, dict) else int(raw)
    except (TypeError, ValueError):
        logger.warning("Could not parse Fear & Greed value: %s", raw)
        return None


def _render_kpi_cards(market: dict[str, Any]) -> None:
    """Render the three top KPI metric cards (Fear & Greed, Market Cap, BTC Dominance)."""
    col1, col2, col3 = st.columns(3)

    # Fear & Greed
    with col1, st.container(border=True):
        fg_val = _parse_fear_greed(market.get("fear_greed"))
        if fg_val is not None:
            label = _fear_greed_label(fg_val)
            st.metric(t("analytics.fear_greed"), f"{fg_val}", delta=label, delta_color="off")
        else:
            st.metric(t("analytics.fear_greed"), "—")
            st.caption(t("analytics.data_unavailable"))

    # Total market capitalisation
    with col2, st.container(border=True):
        raw_mcap = market.get("total_market_cap")
        try:
            mcap_str = f"${float(raw_mcap or 0) / 1e12:.2f} T" if raw_mcap is not None else "—"
        except (TypeError, ValueError):
            mcap_str = "—"
        st.metric(t("analytics.market_cap"), mcap_str)
        if mcap_str == "—":
            st.caption(t("analytics.data_unavailable"))

    # BTC dominance
    with col3, st.container(border=True):
        raw_dom = market.get("btc_dominance")
        try:
            dom_str = f"{float(raw_dom or 0):.1f}%" if raw_dom is not None else "—"
        except (TypeError, ValueError):
            dom_str = "—"
        st.metric(t("analytics.btc_dominance"), dom_str)
        if dom_str == "—":
            st.caption(t("analytics.data_unavailable"))


def _render_performance_heatmap(market: dict[str, Any]) -> None:
    """Render a crypto performance heatmap: symbols x periods (24h, 7d, 30d)."""
    heatmap_data: list[dict[str, Any]] = market.get("heatmap") or []

    if not heatmap_data:
        # Styled empty state inside a bordered container
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center; padding:2rem; color:#888;'>"
                f"{t('analytics.no_heatmap')}<br>"
                f"<small>{t('analytics.backend_hint')}</small>"
                "</div>",
                unsafe_allow_html=True,
            )
        return

    symbols = [d.get("symbol") or "?" for d in heatmap_data]
    periods = ["24h"]

    # Build z_data — API only provides change_pct (24h)
    z_data: list[list[float]] = [[float(d.get("change_pct") or 0) for d in heatmap_data]]

    fig = go.Figure(
        go.Heatmap(
            z=z_data,
            x=symbols,
            y=periods,
            colorscale="RdYlGn",
            zmid=0,
            text=[[f"{v:+.1f}%" for v in row] for row in z_data],
            texttemplate="%{text}",
            textfont={"size": 11},
            hoverongaps=False,
        )
    )
    fig.update_layout(
        height=260,
        title={"text": t("analytics.heatmap_chart_title"), "font": {"size": 13}},
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_movers_table(movers: list[dict[str, Any]]) -> None:
    """Render a compact styled table for top gainers or losers."""
    rows = [
        {
            t("analytics.col_crypto"): m.get("symbol") or "?",
            t("analytics.col_price"): f"${float(m.get('price') or 0):,.4f}",
            t("analytics.col_change_24h"): f"{float(m.get('change_pct') or 0):+.2f}%",
            t("analytics.col_volume_24h"): f"${float(m.get('volume_24h') or 0):,.0f}",
        }
        for m in movers
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_gainers_losers(market: dict[str, Any]) -> None:
    """Render the Top Gainers and Top Losers side-by-side tables."""
    col_gain, col_lose = st.columns(2)

    with col_gain, st.container(border=True):
        st.markdown(f"### {t('analytics.gainers')}")
        gainers: list[dict[str, Any]] = market.get("top_gainers") or []
        if gainers:
            _render_movers_table(gainers)
        else:
            st.markdown(
                f"<div style='text-align:center; padding:1.5rem; color:#888;'>{t('analytics.no_gainers')}</div>",
                unsafe_allow_html=True,
            )

    with col_lose, st.container(border=True):
        st.markdown(f"### {t('analytics.losers')}")
        losers: list[dict[str, Any]] = market.get("top_losers") or []
        if losers:
            _render_movers_table(losers)
        else:
            st.markdown(
                f"<div style='text-align:center; padding:1.5rem; color:#888;'>{t('analytics.no_losers')}</div>",
                unsafe_allow_html=True,
            )


def _render_correlation_matrix() -> None:
    """Build and display a Plotly correlation heatmap from daily close prices."""
    close_series: dict[str, list[float]] = {}
    min_len: int | None = None

    # Fetch OHLCV for each symbol and collect closing prices
    for sym in _CORRELATION_SYMBOLS:
        data = _fetch_ohlcv_for_symbol(sym)
        if data:
            closes = [float(d.get("price_close") or 0) for d in data]
            close_series[sym] = closes
            min_len = min(min_len, len(closes)) if min_len is not None else len(closes)

    if len(close_series) < 2 or not min_len:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center; padding:2rem; color:#888;'>"
                f"{t('analytics.correlation_insufficient')}<br>"
                f"<small>{t('analytics.correlation_min_hint')}</small>"
                "</div>",
                unsafe_allow_html=True,
            )
        return

    # Align all series to the same length (most recent candles) then compute corr
    aligned = {sym: vals[-min_len:] for sym, vals in close_series.items()}
    df_closes = pd.DataFrame(aligned)
    corr = df_closes.pct_change().dropna().corr()

    syms = list(corr.columns)
    z_vals = corr.values.tolist()
    text_vals = [[f"{v:.2f}" for v in row] for row in z_vals]

    fig = go.Figure(
        go.Heatmap(
            z=z_vals,
            x=syms,
            y=syms,
            colorscale="RdYlGn",
            zmin=-1,
            zmax=1,
            zmid=0,
            text=text_vals,
            texttemplate="%{text}",
            textfont={"size": 12},
        )
    )
    fig.update_layout(
        height=420,
        title={"text": t("analytics.correlation_chart_title"), "font": {"size": 13}},
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_fear_greed_gauge(value: int) -> None:
    """Render a Plotly gauge chart for the Fear & Greed index."""
    label = _fear_greed_label(value)
    color = _fear_greed_color(value)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={
                "text": t("analytics.sentiment_label", label=label),
                "font": {"size": 16, "color": "#fafafa"},
            },
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#fafafa"},
                "bar": {"color": color},
                "bgcolor": "#161b22",
                "steps": [
                    {"range": [0, 25], "color": "#b71c1c"},
                    {"range": [25, 45], "color": "#e64a19"},
                    {"range": [45, 55], "color": "#f9a825"},
                    {"range": [55, 75], "color": "#558b2f"},
                    {"range": [75, 100], "color": "#1b5e20"},
                ],
                "threshold": {
                    "line": {"color": "#fafafa", "width": 3},
                    "thickness": 0.75,
                    "value": value,
                },
            },
            number={"font": {"color": "#fafafa"}},
        )
    )
    fig.update_layout(height=320, **_DARK_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def page() -> None:
    """Render the Analytics page."""
    st.header(t("analytics.header"))

    market = _fetch_market()

    # Early exit with a styled error state if the API is unavailable
    if market is None:
        with st.container(border=True):
            st.error(t("analytics.backend_unavailable"))
            st.info(t("analytics.backend_hint"))
        return

    # --- Section 1: KPI cards (Fear & Greed / Market Cap / BTC Dominance) ---
    _render_kpi_cards(market)

    st.divider()

    # --- Section 2: Performance heatmap across 24h / 7d / 30d ---
    st.markdown(f"### {t('analytics.heatmap_title')}")
    with st.container(border=True):
        _render_performance_heatmap(market)

    st.divider()

    # --- Section 3: Top movers (gainers and losers over 24h) ---
    st.markdown(f"### {t('analytics.top_movers')}")
    _render_gainers_losers(market)

    st.divider()

    # --- Section 4: Correlation matrix computed from 90-day daily closes ---
    st.markdown(f"### {t('analytics.correlation_title')}")
    with st.container(border=True):
        _render_correlation_matrix()

    st.divider()

    # --- Section 5: Fear & Greed gauge (full visual) ---
    st.markdown(f"### {t('analytics.fear_greed_gauge')}")
    fg_val = _parse_fear_greed(market.get("fear_greed"))
    if fg_val is not None:
        with st.container(border=True):
            _render_fear_greed_gauge(fg_val)
    else:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center; padding:2rem; color:#888;'>"
                f"{t('analytics.fear_greed_unavailable')}<br>"
                f"<small>{t('analytics.fear_greed_source')}</small>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # --- Section 6: Market regime and volatility (Semaine 3) ---
    st.markdown(f"### {t('analytics.market_regime_title')}")
    metrics = _fetch_system_metrics()
    if metrics:
        col_regime, col_vol = st.columns(2)
        with col_regime, st.container(border=True):
            st.markdown(f"#### {t('analytics.regime_label')}")
            regime = metrics.get("market_regime")
            render_regime_badge(regime)

        with col_vol, st.container(border=True):
            st.markdown(f"#### {t('analytics.volatility_label')}")
            volatility_data = metrics.get("volatility", {})
            if volatility_data:
                rows = [
                    {
                        t("analytics.col_crypto"): sym,
                        t("analytics.col_volatility"): f"{float(vol):.2f}%",
                    }
                    for sym, vol in volatility_data.items()
                ]
                df_vol = pd.DataFrame(rows)
                st.dataframe(df_vol, use_container_width=True, hide_index=True)
            else:
                st.info(t("analytics.volatility_unavailable"))
    else:
        with st.container(border=True):
            st.info(t("analytics.backend_unavailable"))


page()
