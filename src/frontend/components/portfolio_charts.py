"""Portfolio visualization components: pie chart (allocation) and line chart (history)."""

from __future__ import annotations

import logging
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from src.frontend.components.candlestick import _DARK_LAYOUT
from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Color palette for pie chart allocation (assets)
_ALLOCATION_COLORS: list[str] = [
    "#26c6a0",  # teal
    "#42a5f5",  # blue
    "#ab47bc",  # purple
    "#ec407a",  # pink
    "#ff7043",  # orange
    "#ffb74d",  # amber
    "#66bb6a",  # green
    "#29b6f6",  # light blue
]


def render_portfolio_pie(allocation: dict[str, float]) -> None:
    """Render asset allocation pie chart using Plotly.

    Parameters
    ----------
    allocation : dict[str, float]
        Symbol -> value mapping (e.g., {"BTC": 5000, "ETH": 3000}).
    """
    if not allocation:
        st.info(t("portfolio.allocation_empty"))
        return

    symbols = list(allocation.keys())
    values = list(allocation.values())

    fig = go.Figure(
        go.Pie(
            labels=symbols,
            values=values,
            marker={"colors": _ALLOCATION_COLORS[: len(symbols)]},
            textposition="inside",
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        height=350,
        title={"text": t("portfolio.allocation_title"), "font": {"size": 13}},
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_portfolio_history_chart(history: list[dict[str, Any]]) -> None:
    """Render portfolio value history as a line chart with Plotly.

    Parameters
    ----------
    history : list[dict[str, Any]]
        List of records with 'timestamp' and 'total_value' keys.
    """
    if not history:
        st.info(t("portfolio.history_empty"))
        return

    dates: list[str] = []
    values: list[float] = []

    for record in history:
        ts = record.get("timestamp")
        val = record.get("total_value")
        if ts and val is not None:
            try:
                values.append(float(val))
                dates.append(str(ts))
            except (TypeError, ValueError):
                logger.warning("Invalid total_value in history record: %r", val)

    if not dates or not values:
        st.info(t("portfolio.history_empty"))
        return

    # Color based on net gain/loss
    final_color = "#26a69a" if values[-1] >= (values[0] if values else 0) else "#ef5350"
    fill_color = "rgba(38,166,154,0.1)" if values[-1] >= (values[0] if values else 0) else "rgba(239,83,80,0.1)"

    fig = go.Figure(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines+markers",
            name=t("portfolio.value_label"),
            line={"color": final_color, "width": 2},
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title=t("portfolio.date_label"),
        yaxis_title=t("portfolio.value_label"),
        height=350,
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)
