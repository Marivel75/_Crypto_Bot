"""Candlestick chart component with volume subplot and Bollinger overlay."""

from __future__ import annotations

import logging
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Shared dark layout applied to all Plotly figures in this frontend.
# Colors chosen to be legible in both dark and light Streamlit themes:
#   - paper/plot bg match Streamlit's dark sidebar (#0e1117)
#   - font color is near-white (#e0e0e0) — visible on dark bg, contrasts well on light
#   - gridlines use a subtle mid-gray that does not overpower data
_DARK_LAYOUT: dict[str, Any] = {
    "template": "plotly_dark",
    "paper_bgcolor": "#0e1117",
    "plot_bgcolor": "#161b22",
    "font": {"color": "#e0e0e0", "size": 12, "family": "Inter, sans-serif"},
    "margin": {"l": 60, "r": 30, "t": 50, "b": 40},
    "legend": {
        "bgcolor": "rgba(14,17,23,0.7)",
        "bordercolor": "rgba(255,255,255,0.1)",
        "borderwidth": 1,
        "font": {"size": 11},
    },
    "xaxis_rangeslider_visible": False,
}

# Candle color palette — teal/red chosen for accessibility (avoid pure green/red).
_COLOR_BULL: str = "#26c6a0"  # teal-green for bullish candles
_COLOR_BEAR: str = "#ef5350"  # warm red for bearish candles


def render_candlestick(
    ohlcv_data: list[dict[str, Any]],
    indicators: dict[str, Any] | None = None,
    symbol: str = "",
    timeframe: str = "",
) -> go.Figure:
    """Build a candlestick + volume figure with optional Bollinger Bands overlay.

    Args:
        ohlcv_data: List of OHLCV dicts (keys: timestamp, price_open/high/low/close, volume_24h).
            Returns an empty figure with a friendly message when the list is empty or None.
        indicators: Optional indicator dict with bollinger_upper/middle/lower keys.
            Bands are skipped when any required key is missing.
        symbol: Crypto symbol used in the chart title (e.g. "BTCUSDT").
        timeframe: Timeframe label appended to the title (e.g. "4h").

    Returns:
        Plotly Figure ready for ``st.plotly_chart``.
    """
    if not ohlcv_data:
        logger.warning("render_candlestick called with empty ohlcv_data for %s %s", symbol, timeframe)
        fig = go.Figure()
        fig.update_layout(
            title=t("candlestick.no_data_title"),
            **_DARK_LAYOUT,
            height=550,
            annotations=[
                {
                    "text": t("candlestick.no_data_annotation"),
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 18, "color": "#888"},
                }
            ],
        )
        return fig

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=("", "Volume"),  # top row has no subtitle; title comes from layout
    )

    timestamps = [d.get("timestamp", "") for d in ohlcv_data]
    opens = [float(d.get("price_open") or 0) for d in ohlcv_data]
    highs = [float(d.get("price_high") or 0) for d in ohlcv_data]
    lows = [float(d.get("price_low") or 0) for d in ohlcv_data]
    closes = [float(d.get("price_close") or 0) for d in ohlcv_data]
    volumes = [float(d.get("volume_24h") or 0) for d in ohlcv_data]

    # --- Candlestick trace ---
    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="OHLCV",
            increasing_line_color=_COLOR_BULL,
            increasing_fillcolor=_COLOR_BULL,
            decreasing_line_color=_COLOR_BEAR,
            decreasing_fillcolor=_COLOR_BEAR,
            whiskerwidth=0.5,
        ),
        row=1,
        col=1,
    )

    # --- Bollinger Bands overlay (optional) ---
    if indicators:
        bb_upper = indicators.get("bollinger_upper")
        bb_middle = indicators.get("bollinger_middle")
        bb_lower = indicators.get("bollinger_lower")
        if bb_upper is not None and bb_lower is not None:
            n = len(timestamps)
            # Upper/lower bands share the same yellow accent; middle is light blue
            _add_bb_line(fig, timestamps, bb_upper, n, "BB Upper", "#f9a825", "dash")
            if bb_middle is not None:
                _add_bb_line(fig, timestamps, bb_middle, n, "BB Middle", "#64b5f6", "dot")
            _add_bb_line(fig, timestamps, bb_lower, n, "BB Lower", "#f9a825", "dash")
        else:
            logger.debug("Bollinger upper/lower missing for %s; skipping overlay", symbol)

    # --- Volume bars — color matches candle direction ---
    vol_colors = [_COLOR_BULL if c >= o else _COLOR_BEAR for o, c in zip(opens, closes, strict=True)]
    fig.add_trace(
        go.Bar(
            x=timestamps,
            y=volumes,
            name="Volume",
            marker_color=vol_colors,
            opacity=0.55,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    title = f"{symbol} - {timeframe}".strip(" -") if symbol or timeframe else "Candlestick"
    fig.update_layout(
        title={"text": title, "font": {"size": 16, "color": "#e0e0e0"}},
        **_DARK_LAYOUT,
        height=580,
    )

    # Price axis — right-side labels, subtle grid
    fig.update_yaxes(
        title_text=t("candlestick.price_axis"),
        title_font={"size": 11},
        gridcolor="rgba(255,255,255,0.06)",
        zerolinecolor="rgba(255,255,255,0.1)",
        row=1,
        col=1,
    )
    # Volume axis — no title needed (subplot_title covers it), minimal grid
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        zerolinecolor="rgba(255,255,255,0.1)",
        row=2,
        col=1,
    )
    # Shared x-axis styling
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.04)",
        showspikes=True,
        spikecolor="rgba(255,255,255,0.3)",
        spikethickness=1,
    )

    return fig


def _add_bb_line(
    fig: go.Figure,
    timestamps: list[str],
    value: Any,
    n: int,
    name: str,
    color: str,
    dash: str = "dot",
) -> None:
    """Add a single Bollinger Band line to row 1 of the figure.

    Accepts either a scalar (repeated across all timestamps) or a list/tuple
    of per-bar values.  Invalid values default to 0.0 with a warning logged.

    Args:
        fig: The target subplot figure.
        timestamps: X-axis values (one per bar).
        value: Scalar or iterable of band values.
        n: Number of data points — used when value is a scalar.
        name: Trace legend label.
        color: Hex color string for the line.
        dash: Plotly dash style ("dash", "dot", "dashdot", "solid").
    """
    try:
        if isinstance(value, (list, tuple)):
            y_vals = [float(v) if v is not None else 0.0 for v in value]
        else:
            y_vals = [float(value)] * n
    except (TypeError, ValueError) as exc:
        logger.warning("Could not convert BB value for %s: %s", name, exc)
        return

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=y_vals,
            mode="lines",
            name=name,
            line={"color": color, "width": 1.2, "dash": dash},
            opacity=0.85,
        ),
        row=1,
        col=1,
    )
