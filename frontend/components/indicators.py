"""Indicator display component — summary metrics for RSI, Bollinger, MACD."""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from frontend.i18n import t

logger = logging.getLogger(__name__)

_RSI_OVERBOUGHT: float = 70.0
_RSI_OVERSOLD: float = 30.0


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rsi_label(rsi: float) -> str:
    if rsi >= _RSI_OVERBOUGHT:
        return t("indicators.rsi_overbought")
    if rsi <= _RSI_OVERSOLD:
        return t("indicators.rsi_oversold")
    return t("indicators.rsi_neutral")


def _bb_position_label(close: float, bb_upper: float, bb_lower: float) -> str:
    """Classify price position relative to Bollinger Bands."""
    band_width = bb_upper - bb_lower
    if band_width <= 0:
        return t("indicators.bb_middle")
    position = (close - bb_lower) / band_width  # 0 = at lower, 1 = at upper
    if position > 1.0:
        return t("indicators.bb_above_upper")
    if position > 0.75:
        return t("indicators.bb_near_upper")
    if position < 0.0:
        return t("indicators.bb_below_lower")
    if position < 0.25:
        return t("indicators.bb_near_lower")
    return t("indicators.bb_middle")


def _macd_label(macd_line: float, macd_signal: float) -> str:
    if macd_line > macd_signal:
        return t("indicators.macd_bullish")
    if macd_line < macd_signal:
        return t("indicators.macd_bearish")
    return t("indicators.macd_neutral")


def render_indicator_summary(latest_signal: dict[str, Any] | None) -> None:
    """Render a 3-column metric row: RSI, Bollinger position, MACD.

    Args:
        latest_signal: Most recent signal dict from GET /signals.
            Expected keys: rsi_14, close, bb_upper, bb_lower, macd_line, macd_signal.
    """
    if latest_signal is None:
        st.info(t("indicators.not_available"))
        return

    col_rsi, col_bb, col_macd = st.columns(3)

    # RSI
    rsi = _safe_float(latest_signal.get("rsi_14"))
    with col_rsi:
        if rsi is not None:
            zone = _rsi_label(rsi)
            delta_color = "inverse" if rsi >= _RSI_OVERBOUGHT else "normal"
            st.metric("RSI (14)", f"{rsi:.1f}", delta=zone, delta_color=delta_color)
        else:
            st.metric("RSI (14)", "-")

    # Bollinger position
    close = _safe_float(latest_signal.get("close"))
    bb_upper = _safe_float(latest_signal.get("bb_upper"))
    bb_lower = _safe_float(latest_signal.get("bb_lower"))
    with col_bb:
        if close is not None and bb_upper is not None and bb_lower is not None:
            label = _bb_position_label(close, bb_upper, bb_lower)
            band_pct = (close - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper != bb_lower else 50
            st.metric("Bollinger", label, delta=f"{band_pct:.0f}% in band")
        else:
            st.metric("Bollinger", "-")

    # MACD
    macd_line = _safe_float(latest_signal.get("macd_line"))
    macd_signal = _safe_float(latest_signal.get("macd_signal"))
    with col_macd:
        if macd_line is not None and macd_signal is not None:
            label = _macd_label(macd_line, macd_signal)
            hist = _safe_float(latest_signal.get("macd_histogram"))
            delta_str = f"{hist:+.4f}" if hist is not None else None
            st.metric("MACD", label, delta=delta_str)
        else:
            st.metric("MACD", "-")
