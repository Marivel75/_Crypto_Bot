"""Market regime badge component — displays bull/bear/sideways status."""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Regime color and styling configuration
_REGIME_CONFIG: dict[str, dict[str, str]] = {
    "BULL": {
        "bg": "rgba(38, 166, 154, 0.15)",
        "border": "#26a69a",
        "text": "#26a69a",
        "icon": "📈",
    },
    "BEAR": {
        "bg": "rgba(239, 83, 80, 0.15)",
        "border": "#ef5350",
        "text": "#ef5350",
        "icon": "📉",
    },
    "SIDEWAYS": {
        "bg": "rgba(255, 235, 59, 0.15)",
        "border": "#ffeb3b",
        "text": "#ffeb3b",
        "icon": "➡️",
    },
}


def render_regime_badge(regime: str | None) -> None:
    """Render a colored badge for market regime.

    Parameters
    ----------
    regime : str | None
        One of "BULL", "BEAR", "SIDEWAYS", or None.
    """
    if regime is None:
        regime = "SIDEWAYS"

    regime_upper = str(regime).upper()
    if regime_upper not in _REGIME_CONFIG:
        logger.warning("Unknown regime %r, rendering as SIDEWAYS", regime)
        regime_upper = "SIDEWAYS"

    config = _REGIME_CONFIG[regime_upper]
    label = t(f"analytics.regime_{regime_upper.lower()}")

    st.markdown(
        f"""
        <div style="
            background: {config['bg']};
            border: 2px solid {config['border']};
            border-radius: 8px;
            padding: 12px 16px;
            text-align: center;
            margin: 0.5rem 0;
        ">
            <span style="font-size: 1.5rem; margin-right: 8px;">{config['icon']}</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: {config['text']};">
                {label}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
