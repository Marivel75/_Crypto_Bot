"""Page 1 — Dashboard principal (Noah, Trader).

Layout: symbol/TF selectors -> candlestick chart + news panel -> signals + multi-TF table.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.components.candlestick import render_candlestick
from src.frontend.components.indicators import (
    render_indicator_summary,
    render_multi_timeframe_table,
)
from src.frontend.components.news_feed import render_news_card
from src.frontend.components.signal_card import render_signals_panel
from src.frontend.config import frontend_settings
from src.frontend.i18n import t

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# Data fetchers — thin wrappers over the shared API client
# ---------------------------------------------------------------------------


@st.cache_data(ttl=60)
def _fetch_ohlcv(symbol: str, timeframe: str) -> list[dict[str, Any]] | None:
    return _get_client().fetch_ohlcv(symbol, timeframe)


@st.cache_data(ttl=60)
def _fetch_indicators(symbol: str, timeframe: str) -> list[dict[str, Any]] | None:
    return _get_client().fetch_indicators(symbol, timeframe)


@st.cache_data(ttl=30)
def _fetch_signals(symbol: str) -> list[dict[str, Any]] | None:
    return _get_client().fetch_signals(symbol)


@st.cache_data(ttl=120)
def _fetch_news() -> list[dict[str, Any]] | None:
    return _get_client().fetch_news(limit=5)


@st.cache_data(ttl=60)
def _fetch_multi_tf(symbol: str) -> list[dict[str, Any]] | None:
    return _get_client().fetch_multi_timeframe(symbol)


def _latest_indicator(indicators: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Return the most recent indicator record from a list, or None."""
    if not indicators:
        return None
    return indicators[0]


def _check_api_status() -> bool:
    """Probe the health endpoint and return True if the API is reachable."""
    result = _get_client().health()  # S11: uses proper /api/v1/health endpoint
    return result is not None


# ---------------------------------------------------------------------------
# Empty-state helpers — styled cards shown when data is absent
# ---------------------------------------------------------------------------


def _render_empty_chart(symbol: str, timeframe: str) -> None:
    """Render a styled empty-state card when no OHLCV data is available."""
    st.markdown(
        f"""
        <div style="
            border: 1px solid #2d2d2d;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            background: #1a1a2e;
            color: #8b8b9e;
            margin: 1rem 0;
        ">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;"><i class="icon-bar-chart-2" style="font-size:2.5rem;"></i></div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #c8c8d4; margin-bottom: 0.4rem;">
                {t("dashboard.no_data_title")}
            </div>
            <div style="font-size: 0.9rem;">
                {t("dashboard.no_ohlcv_data", symbol=symbol, timeframe=timeframe)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_news() -> None:
    """Render a styled empty-state card when no news articles are available."""
    _title = t("dashboard.no_recent_news_title")
    _body = t("dashboard.no_recent_news_body")
    st.markdown(
        f"""
        <div style="
            border: 1px solid #2d2d2d;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            background: #1a1a2e;
            color: #8b8b9e;
            margin: 0.5rem 0;
        ">
            <div style="font-size: 2rem; margin-bottom: 0.4rem;"><i class="icon-newspaper" style="font-size:2rem;"></i></div>
            <div style="font-size: 0.95rem; font-weight: 600; color: #c8c8d4; margin-bottom: 0.3rem;">
                {_title}
            </div>
            <div style="font-size: 0.85rem;">
                {_body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def page() -> None:
    """Render the dashboard page."""
    # --- Page header with API status indicator ---
    header_col, status_col = st.columns([5, 1])
    with header_col:
        st.header(t("dashboard.header"))
    with status_col:
        st.write("")  # vertical alignment nudge
        api_ok = _check_api_status()
        if api_ok:
            st.success(t("dashboard.api_connected"), icon=":material/check_circle:")
        else:
            st.error(t("dashboard.api_offline"), icon=":material/cancel:")

    # --- Symbol / timeframe selectors + refresh button ---
    col_sym, col_tf, col_refresh = st.columns([2, 1, 1])
    with col_sym:
        # tracked_symbols comes from frontend_settings (env-driven list)
        symbol: str = st.selectbox(
            t("dashboard.crypto"),
            frontend_settings.tracked_symbols,
            index=0,
        )
    with col_tf:
        # timeframes ordered from short to long; default index 3 = "4h"
        timeframe: str = st.selectbox(
            t("dashboard.timeframe"),
            frontend_settings.timeframes,
            index=3,
        )
    with col_refresh:
        st.write("")
        if st.button(t("dashboard.refresh"), use_container_width=True, type="primary"):
            # Clear all cached API responses and reload the page
            st.cache_data.clear()
            st.rerun()

    # --- Candlestick chart + News feed ---
    col_chart, col_news = st.columns([3, 1])

    with col_chart, st.container(border=True):
        st.subheader(t("dashboard.candlestick_header"))

        ohlcv = _fetch_ohlcv(symbol, timeframe)
        indicators = _fetch_indicators(symbol, timeframe)
        latest_ind = _latest_indicator(indicators)

        if ohlcv is None:
            # API error already surfaced by the client; show contextual note
            st.error(
                t("dashboard.chart_unavailable"),
                icon=":material/warning:",
            )
        elif not ohlcv:
            _render_empty_chart(symbol, timeframe)
        else:
            fig = render_candlestick(ohlcv, latest_ind, symbol, timeframe)
            st.plotly_chart(fig, use_container_width=True)

        # Indicator pills always rendered below the chart (or empty state)
        render_indicator_summary(latest_ind)

    with col_news, st.container(border=True):
        st.subheader(t("dashboard.news_header"))

        news = _fetch_news()
        if news is None:
            st.error(t("dashboard.news_unavailable"), icon=":material/warning:")
        elif not news:
            _render_empty_news()
        else:
            for article in news:
                render_news_card(article)

    # --- Signals + Multi-timeframe table ---
    col_signals, col_mtf = st.columns(2)

    with col_signals, st.container(border=True):
        # render_signals_panel manages its own subheader internally
        signals = _fetch_signals(symbol)
        render_signals_panel(signals)

    with col_mtf, st.container(border=True):
        st.subheader(t("dashboard.multi_tf_header"))
        mtf_data = _fetch_multi_tf(symbol)
        render_multi_timeframe_table(mtf_data)


page()
