"""Indicator display components — summary metrics and multi-timeframe table."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Thresholds for Bollinger position labelling (price_vs_bollinger range: -1 to 1).
# Values above _BB_UPPER_THRESHOLD indicate price is approaching/above the upper band.
_BB_UPPER_THRESHOLD: float = 0.5
_BB_LOWER_THRESHOLD: float = -0.5

# Minimum absolute slope to classify a trend as directional (up/down vs. flat).
_TREND_SLOPE_THRESHOLD: float = 0.001

# RSI zones used for color-coded help text shown alongside the metric.
_RSI_OVERBOUGHT: float = 70.0
_RSI_OVERSOLD: float = 30.0


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure.

    Args:
        value: Any value to attempt conversion on.

    Returns:
        Float representation or None if conversion is not possible.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid numeric value %r: %s", value, exc)
        return None


def _rsi_label(rsi: float) -> str:
    """Return a human-readable RSI zone label.

    Args:
        rsi: RSI value in [0, 100].

    Returns:
        One of "Overbought", "Oversold", or "Neutral".
    """
    if rsi >= _RSI_OVERBOUGHT:
        return t("indicators.rsi_overbought")
    if rsi <= _RSI_OVERSOLD:
        return t("indicators.rsi_oversold")
    return t("indicators.rsi_neutral")


def _bb_label(bb_pos: float) -> str:
    """Return a human-readable Bollinger position label.

    Args:
        bb_pos: Normalised price-vs-bollinger value (typically −1 to +1).

    Returns:
        Descriptive string for the position relative to the bands.
    """
    if bb_pos > 1.0:
        return t("indicators.bb_above_upper")
    if bb_pos > _BB_UPPER_THRESHOLD:
        return t("indicators.bb_near_upper")
    if bb_pos < -1.0:
        return t("indicators.bb_below_lower")
    if bb_pos < _BB_LOWER_THRESHOLD:
        return t("indicators.bb_near_lower")
    return t("indicators.bb_middle")


def render_indicator_summary(indicator: dict[str, Any] | None) -> None:
    """Render a 3-column metric summary: RSI, Bollinger position, and Trend.

    Displays color-coded context (Streamlit ``st.metric`` delta colors) to help
    users interpret values at a glance.  Gracefully handles None or missing keys.

    Args:
        indicator: Dict with optional keys rsi, price_vs_bollinger, trend_type,
            trend_slope.  Pass None to display an informational placeholder.
    """
    if indicator is None:
        st.info(t("indicators.not_available"))
        return

    col_rsi, col_bb, col_trend = st.columns(3)

    # --- RSI ---
    rsi = _safe_float(indicator.get("rsi"))
    with col_rsi:
        if rsi is not None:
            rsi_zone = _rsi_label(rsi)
            # Use delta_color="inverse" so oversold (low RSI) shows green, overbought red
            delta_color: str = "normal"
            if rsi >= _RSI_OVERBOUGHT:
                delta_color = "inverse"  # high RSI -> red delta (caution)
            elif rsi <= _RSI_OVERSOLD:
                delta_color = "normal"  # low RSI -> green delta (potential buy)
            st.metric("RSI", f"{rsi:.1f}", delta=rsi_zone, delta_color=delta_color)  # type: ignore[arg-type]
        else:
            st.metric("RSI", "-")

    # --- Bollinger Bands position ---
    bb_pos = _safe_float(indicator.get("price_vs_bollinger"))
    with col_bb:
        if bb_pos is not None:
            label = _bb_label(bb_pos)
            st.metric("Bollinger", label, delta=f"{bb_pos:+.2f}")
        else:
            st.metric("Bollinger", "-")

    # --- Trend ---
    trend = indicator.get("trend_type")
    slope = _safe_float(indicator.get("trend_slope"))
    with col_trend:
        trend_label = str(trend) if trend else "-"
        delta_str = f"{slope:+.4f}" if slope is not None else None
        st.metric("Trend", trend_label, delta=delta_str)


def render_multi_timeframe_table(tf_data: list[dict[str, Any]] | None) -> None:
    """Render a summary table with one row per timeframe showing key indicators.

    Adds directional arrows to the trend column based on trend_slope magnitude.
    Handles None/empty input gracefully without raising exceptions.

    Args:
        tf_data: List of dicts, each with keys timeframe, rsi, price_vs_bollinger,
            trend_type, and optionally trend_slope.  None or empty list shows a
            placeholder message.
    """
    if not tf_data:
        st.info(t("indicators.multi_tf_unavailable"))
        return

    rows = []
    for item in tf_data:
        rsi = _safe_float(item.get("rsi"))
        bb = _safe_float(item.get("price_vs_bollinger"))
        trend = item.get("trend_type") or "-"
        slope = _safe_float(item.get("trend_slope"))

        # Derive directional arrow from slope magnitude
        if slope is not None:
            if slope > _TREND_SLOPE_THRESHOLD:
                arrow = "↑"
            elif slope < -_TREND_SLOPE_THRESHOLD:
                arrow = "↓"
            else:
                arrow = "→"
        else:
            arrow = "-"

        # Annotate RSI with zone for quick reading
        rsi_str = "-"
        if rsi is not None:
            rsi_str = f"{rsi:.1f} ({_rsi_label(rsi)})"

        rows.append(
            {
                "TF": item.get("timeframe", "?"),
                "RSI": rsi_str,
                "Bollinger": f"{bb:.2f} - {_bb_label(bb)}" if bb is not None else "-",
                "Trend": f"{trend} {arrow}",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
