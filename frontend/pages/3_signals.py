"""Page 3 — Exploration des signaux techniques."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st

from frontend.api_client import APIClient
from frontend.config import frontend_settings
from frontend.i18n import t
from frontend.utils import extract_symbols, extract_timeframes, fmt_ts


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=300)
def _fetch_available() -> tuple[list[str], list[str]]:
    data = _get_client().fetch_symbols()
    if data:
        return extract_symbols(data), extract_timeframes(data)
    return frontend_settings.tracked_symbols, frontend_settings.timeframes


@st.cache_data(ttl=60)
def _fetch(symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]] | None:
    return _get_client().fetch_signals(symbol, timeframe, limit=limit)


def _fmt(val: Any, decimals: int) -> float | None:
    if val is None:
        return None
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None




def page() -> None:
    st.header(t("signals.header"))

    available_symbols, available_timeframes = _fetch_available()

    col_sym, col_tf, col_lim = st.columns([2, 1, 1])
    with col_sym:
        symbol = st.selectbox(t("signals.symbol"), available_symbols)
    with col_tf:
        tf_default = available_timeframes.index("1d") if "1d" in available_timeframes else 0
        timeframe = st.selectbox(t("signals.timeframe"), available_timeframes, index=tf_default)
    with col_lim:
        limit = st.slider(t("signals.limit"), min_value=10, max_value=500, value=100, step=10)

    data = _fetch(symbol, timeframe, limit)

    if data is None:
        st.error(t("signals.no_data", symbol=symbol, timeframe=timeframe))
        return
    if not data:
        st.warning(t("signals.no_data", symbol=symbol, timeframe=timeframe))
        return

    rows = []
    for row in data:
        rows.append({
            "Timestamp":   fmt_ts(row.get("timestamp")),
            "Open":        _fmt(row.get("open"), 2),
            "High":        _fmt(row.get("high"), 2),
            "Low":         _fmt(row.get("low"), 2),
            "Close":       _fmt(row.get("close"), 2),
            "Volume":      _fmt(row.get("volume"), 2),
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

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"{len(data)} lignes · {symbol} {timeframe}")


page()
