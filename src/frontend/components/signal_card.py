"""Signal card and panel components with color-coded BUY / SELL / HOLD display."""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Icons used in the card header for quick visual scanning
_DIRECTION_ICONS: dict[str, str] = {
    "BUY": "↑",
    "SELL": "↓",
    "HOLD": "—",
}

# Background and border colors keyed by signal direction.
# These hex values work on both dark and light Streamlit themes:
#   BUY  — teal-green  (accessible, not pure green)
#   SELL — warm red
#   HOLD — medium gray
_DIRECTION_COLORS: dict[str, dict[str, str]] = {
    "BUY": {"bg": "rgba(38, 198, 160, 0.12)", "border": "#26c6a0", "text": "#26c6a0"},
    "SELL": {"bg": "rgba(239, 83, 80, 0.12)", "border": "#ef5350", "text": "#ef5350"},
    "HOLD": {"bg": "rgba(144, 164, 174, 0.10)", "border": "#90a4ae", "text": "#90a4ae"},
}

# Margin safety threshold — below this value we flag a warning to the user
_MARGIN_SAFETY_MIN: float = 2.0


def _direction_css(direction: str) -> str:
    """Return an inline CSS style string for the signal direction badge.

    Args:
        direction: One of "BUY", "SELL", or "HOLD".

    Returns:
        CSS style string suitable for use in an ``st.markdown`` HTML block.
    """
    palette = _DIRECTION_COLORS.get(direction, _DIRECTION_COLORS["HOLD"])
    return (
        f"background:{palette['bg']};"
        f"border-left:4px solid {palette['border']};"
        f"border-radius:6px;"
        f"padding:12px 16px;"
        f"margin-bottom:8px;"
    )


def render_signal_card(signal: dict[str, Any]) -> None:
    """Render a single trading signal as a color-coded styled card.

    Color coding:
    - BUY  — teal-green border and accent
    - SELL — warm red border and accent
    - HOLD — gray border and accent

    Handles missing/None fields gracefully: all optional fields fall back to
    a dash placeholder rather than raising exceptions.

    Args:
        signal: Dict with optional keys signal_type, confidence_score,
            rules_triggered, leverage_suggested, margin_safety, symbol,
            timeframe_primary, entry_price, stop_loss, take_profit_levels.
    """
    direction: str = str(signal.get("signal_type") or "HOLD").upper()
    # Normalise unknown directions to HOLD
    if direction not in _DIRECTION_COLORS:
        logger.debug("Unknown signal direction %r — rendering as HOLD", direction)
        direction = "HOLD"

    palette = _DIRECTION_COLORS[direction]
    icon = _DIRECTION_ICONS.get(direction, "—")
    symbol = signal.get("symbol") or "?"
    tf = signal.get("timeframe_primary") or ""

    confidence = signal.get("confidence_score")
    conf_str = f"{float(confidence):.0%}" if confidence is not None else "—"

    leverage = signal.get("leverage_suggested")
    leverage_str = f"{leverage}x" if leverage is not None else "—"

    css = _direction_css(direction)
    direction_color = palette["text"]

    with st.container(border=True):
        # Color-coded header using raw HTML for precise styling
        tf_html = f'&nbsp;<span style="font-size:0.85rem;color:#888;">({tf})</span>' if tf else ""
        st.markdown(
            f'<div style="{css}">'
            f'<span style="font-size:1.25rem;font-weight:700;color:{direction_color};">'
            f"{icon} {direction}"
            f"</span>"
            f'&nbsp;&nbsp;<span style="font-size:1.1rem;font-weight:600;color:#e0e0e0;">{symbol}</span>'
            f"{tf_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Key metrics in two columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric(t("signal.confidence"), conf_str)
        with col2:
            st.metric(t("signal.leverage"), leverage_str)

        # Entry price, stop loss, take profit (Semaine 3)
        entry = signal.get("entry_price")
        sl = signal.get("stop_loss")
        tp_list = signal.get("take_profit_levels")

        if entry is not None or sl is not None or (tp_list and len(tp_list) > 0):
            st.divider()
            st.caption("**Price Levels**", unsafe_allow_html=True)
            col_entry, col_sl, col_tp = st.columns(3)
            with col_entry:
                entry_str = f"${float(entry):,.2f}" if entry is not None else "—"
                st.metric(t("signal.entry_price"), entry_str)
            with col_sl:
                sl_str = f"${float(sl):,.2f}" if sl is not None else "—"
                st.metric(t("signal.stop_loss"), sl_str)
            with col_tp:
                tp_str = ", ".join(f"${float(p):,.2f}" for p in tp_list[:2]) if tp_list and len(tp_list) > 0 else "—"
                st.metric(t("signal.take_profit"), tp_str)

        # Triggered rules list
        rules: list[Any] = signal.get("rules_triggered") or []
        if rules:
            rule_str = ", ".join(str(r) for r in rules)
            st.caption(t("signal.rules_triggered", rules=rule_str))

        # Margin safety — warn when below threshold
        margin = signal.get("margin_safety")
        if margin is not None:
            try:
                margin_val = float(margin)
            except (TypeError, ValueError):
                logger.warning("Invalid margin_safety value: %r", margin)
                margin_val = None

            if margin_val is not None:
                if margin_val >= _MARGIN_SAFETY_MIN:
                    st.caption(t("signal.margin_ok", value=f"{margin_val:.1f}"))
                else:
                    st.warning(t("signal.margin_low", value=f"{margin_val:.1f}", min=f"{_MARGIN_SAFETY_MIN}x"))


def render_signals_panel(signals: list[dict[str, Any]] | None) -> None:
    """Render a list of signals or an appropriate empty/error state.

    Shows a color-coded card for each signal.  Handles three states:
    - None   — API is unreachable (shows an error message)
    - []     — API returned no active signals (shows info message)
    - [...]  — renders one card per signal

    Args:
        signals: None on API error, empty list when no signals exist, or a
            list of signal dicts as returned by the backend.
    """
    st.subheader(t("signal.active_signals"))

    if signals is None:
        st.error(t("signal.load_error"))
        return

    if not signals:
        st.info(t("signal.no_active"))
        return

    for sig in signals:
        render_signal_card(sig)
