"""Page 1 — Dashboard principal."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st

from frontend.api_client import APIClient
from frontend.components.candlestick import render_candlestick
from frontend.components.indicators import render_indicator_summary
from frontend.config import frontend_settings
from frontend.i18n import t
from frontend.utils import extract_symbols, extract_timeframes

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=300)
def _fetch_available() -> tuple[list[str], list[str]]:
    """Return (symbols, timeframes) available in the database via /ohlcv/symbols.

    Falls back to config values if the API is unreachable.
    """
    data = _get_client().fetch_symbols()
    if data:
        return extract_symbols(data), extract_timeframes(data)
    return frontend_settings.tracked_symbols, frontend_settings.timeframes


@st.cache_data(ttl=60)
def _fetch_signals(symbol: str, timeframe: str, limit: int = 200) -> list[dict[str, Any]] | None:
    return _get_client().fetch_signals(symbol, timeframe, limit=limit)


def _check_api() -> bool:
    return _get_client().get("/health") is not None


def _build_table(signals: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for row in signals:
        rows.append({
            "Timestamp":   _fmt_ts(row.get("timestamp")),
            "Close":       row.get("close"),
            "RSI(14)":     _fmt(row.get("rsi_14"), 2),
            "SMA(20)":     _fmt(row.get("sma_20"), 2),
            "SMA(50)":     _fmt(row.get("sma_50"), 2),
            "EMA(20)":     _fmt(row.get("ema_20"), 2),
            "MACD":        _fmt(row.get("macd_line"), 4),
            "MACD Signal": _fmt(row.get("macd_signal"), 4),
            "MACD Hist":   _fmt(row.get("macd_histogram"), 4),
            "BB Upper":    _fmt(row.get("bb_upper"), 2),
            "BB Middle":   _fmt(row.get("bb_middle"), 2),
            "BB Lower":    _fmt(row.get("bb_lower"), 2),
        })
    return pd.DataFrame(rows)


def _fmt(val: Any, decimals: int) -> float | None:
    if val is None:
        return None
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None


def _fmt_ts(ts: Any) -> str:
    """Format an ISO 8601 timestamp string for display.

    - Midnight timestamps (1d candles) → date only: '2026-04-25'
    - Intraday timestamps              → date + time: '2026-04-25 10:00'
    """
    if not ts:
        return ""
    s = str(ts).replace("Z", "").split("+")[0]  # strip tz
    s = s.replace("T", " ")
    if s.endswith(" 00:00:00") or s.endswith(" 00:00:00.000000"):
        return s[:10]
    return s[:16]  # YYYY-MM-DD HH:MM


def page() -> None:
    header_col, status_col = st.columns([5, 1])
    with header_col:
        st.header(t("dashboard.header"))
    with status_col:
        st.write("")
        if _check_api():
            st.success(t("dashboard.api_connected"), icon=":material/check_circle:")
        else:
            st.error(t("dashboard.api_offline"), icon=":material/cancel:")

    available_symbols, available_timeframes = _fetch_available()

    col_sym, col_tf, col_refresh = st.columns([2, 1, 1])
    with col_sym:
        symbol: str = st.selectbox(t("dashboard.crypto"), available_symbols)
    with col_tf:
        # Default to "1d" if present, else first available timeframe
        tf_default = available_timeframes.index("1d") if "1d" in available_timeframes else 0
        timeframe: str = st.selectbox(t("dashboard.timeframe"), available_timeframes, index=tf_default)
    with col_refresh:
        st.write("")
        if st.button(t("dashboard.refresh"), use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()

    signals = _fetch_signals(symbol, timeframe, limit=200)

    with st.container(border=True):
        st.subheader(t("dashboard.candlestick_header"))
        if signals is None:
            st.error(t("dashboard.chart_unavailable"), icon=":material/warning:")
        elif not signals:
            st.warning(t("dashboard.no_ohlcv_data", symbol=symbol, timeframe=timeframe))
        else:
            # API retourne DESC ; on reverse pour ASC (chronologique)
            chart_data = list(reversed(signals))
            fig = render_candlestick(chart_data, symbol, timeframe)
            st.plotly_chart(fig, use_container_width=True)

        # Métriques : dernière bougie (première en DESC)
        latest = signals[0] if signals else None
        render_indicator_summary(latest)

    if signals:
        with st.container(border=True):
            st.subheader(t("dashboard.signals_header"))
            df = _build_table(signals[:20])
            st.dataframe(df, use_container_width=True, hide_index=True)


page()
