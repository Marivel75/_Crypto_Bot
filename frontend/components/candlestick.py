"""Candlestick chart component with volume subplot, MA overlays, BB overlay, and MACD cross markers."""

from __future__ import annotations

import logging
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from frontend.i18n import t

logger = logging.getLogger(__name__)

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

_COLOR_BULL: str = "#26c6a0"
_COLOR_BEAR: str = "#ef5350"


def _extract(data: list[dict[str, Any]], key: str) -> list[Any]:
    return [d.get(key) for d in data]


def _to_float_or_none(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _compute_macd_crosses(
    macd_lines: list[Any],
    macd_signals: list[Any],
) -> tuple[list[int], list[int]]:
    """Return indices where MACD line crosses above (buy) or below (sell) signal."""
    buy_idx: list[int] = []
    sell_idx: list[int] = []
    for i in range(1, len(macd_lines)):
        ml_c = _to_float_or_none(macd_lines[i])
        ms_c = _to_float_or_none(macd_signals[i])
        ml_p = _to_float_or_none(macd_lines[i - 1])
        ms_p = _to_float_or_none(macd_signals[i - 1])
        if None in (ml_c, ms_c, ml_p, ms_p):
            continue
        if ml_c > ms_c and ml_p <= ms_p:
            buy_idx.append(i)
        elif ml_c < ms_c and ml_p >= ms_p:
            sell_idx.append(i)
    return buy_idx, sell_idx


def _add_line(
    fig: go.Figure,
    timestamps: list[Any],
    values: list[Any],
    name: str,
    color: str,
    dash: str = "solid",
    width: float = 1.0,
    row: int = 1,
) -> None:
    """Add a line trace to the figure (used for MA and BB lines)."""
    y = [_to_float_or_none(v) for v in values]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=y,
            mode="lines",
            name=name,
            line={"color": color, "width": width, "dash": dash},
            opacity=0.85,
            connectgaps=False,
        ),
        row=row,
        col=1,
    )


def render_candlestick(
    signals_data: list[dict[str, Any]],
    symbol: str = "",
    timeframe: str = "",
) -> go.Figure:
    """Build a candlestick + volume figure with MA lines, Bollinger Bands, and MACD cross markers.

    Args:
        signals_data: List of signal dicts from GET /signals (ASC order — oldest first).
            Expected OHLCV fields: timestamp, open, high, low, close, volume.
            Expected indicator fields: sma_20, sma_50, ema_20,
                bb_upper, bb_middle, bb_lower, macd_line, macd_signal.
        symbol: Used in the chart title.
        timeframe: Used in the chart title.
    """
    if not signals_data:
        fig = go.Figure()
        fig.update_layout(
            title=t("candlestick.no_data_title"),
            **_DARK_LAYOUT,
            height=550,
            annotations=[{
                "text": t("candlestick.no_data_annotation"),
                "x": 0.5, "y": 0.5,
                "xref": "paper", "yref": "paper",
                "showarrow": False,
                "font": {"size": 18, "color": "#888"},
            }],
        )
        return fig

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=("", "Volume"),
    )

    timestamps = _extract(signals_data, "timestamp")
    opens  = [float(v or 0) for v in _extract(signals_data, "open")]
    highs  = [float(v or 0) for v in _extract(signals_data, "high")]
    lows   = [float(v or 0) for v in _extract(signals_data, "low")]
    closes = [float(v or 0) for v in _extract(signals_data, "close")]
    volumes = [float(v or 0) for v in _extract(signals_data, "volume")]

    # --- Candlestick ---
    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=opens, high=highs, low=lows, close=closes,
            name="OHLCV",
            increasing_line_color=_COLOR_BULL, increasing_fillcolor=_COLOR_BULL,
            decreasing_line_color=_COLOR_BEAR, decreasing_fillcolor=_COLOR_BEAR,
            whiskerwidth=0.5,
        ),
        row=1, col=1,
    )

    # --- Moving averages overlays ---
    sma_20 = _extract(signals_data, "sma_20")
    sma_50 = _extract(signals_data, "sma_50")
    ema_20 = _extract(signals_data, "ema_20")

    if any(v is not None for v in sma_20):
        _add_line(fig, timestamps, sma_20, "SMA 20", "#42a5f5", width=1.2)
    if any(v is not None for v in sma_50):
        _add_line(fig, timestamps, sma_50, "SMA 50", "#ab47bc", width=1.5)
    if any(v is not None for v in ema_20):
        _add_line(fig, timestamps, ema_20, "EMA 20", "#ffca28", dash="dot", width=1.2)

    # --- Bollinger Bands ---
    bb_upper  = _extract(signals_data, "bb_upper")
    bb_middle = _extract(signals_data, "bb_middle")
    bb_lower  = _extract(signals_data, "bb_lower")

    if any(v is not None for v in bb_upper):
        _add_line(fig, timestamps, bb_upper,  "BB Upper",  "#f9a825", dash="dash", width=1.0)
        _add_line(fig, timestamps, bb_lower,  "BB Lower",  "#f9a825", dash="dash", width=1.0)
        if any(v is not None for v in bb_middle):
            _add_line(fig, timestamps, bb_middle, "BB Middle", "#64b5f6", dash="dot", width=0.9)

    # --- MACD cross markers (▲ buy / ▼ sell) ---
    macd_lines   = _extract(signals_data, "macd_line")
    macd_signals = _extract(signals_data, "macd_signal")
    buy_idx, sell_idx = _compute_macd_crosses(macd_lines, macd_signals)

    if buy_idx:
        fig.add_trace(
            go.Scatter(
                x=[timestamps[i] for i in buy_idx],
                y=[lows[i] * 0.992 for i in buy_idx],
                mode="markers",
                name="MACD Cross ▲",
                marker={
                    "symbol": "triangle-up",
                    "size": 10,
                    "color": _COLOR_BULL,
                    "line": {"color": "#ffffff", "width": 0.5},
                },
                hovertemplate="MACD cross haussier<br>%{x}<extra></extra>",
            ),
            row=1, col=1,
        )

    if sell_idx:
        fig.add_trace(
            go.Scatter(
                x=[timestamps[i] for i in sell_idx],
                y=[highs[i] * 1.008 for i in sell_idx],
                mode="markers",
                name="MACD Cross ▼",
                marker={
                    "symbol": "triangle-down",
                    "size": 10,
                    "color": _COLOR_BEAR,
                    "line": {"color": "#ffffff", "width": 0.5},
                },
                hovertemplate="MACD cross baissier<br>%{x}<extra></extra>",
            ),
            row=1, col=1,
        )

    # --- Volume bars ---
    vol_colors = [_COLOR_BULL if c >= o else _COLOR_BEAR for o, c in zip(opens, closes)]
    fig.add_trace(
        go.Bar(
            x=timestamps, y=volumes,
            name="Volume", marker_color=vol_colors, opacity=0.55, showlegend=False,
        ),
        row=2, col=1,
    )

    # --- Layout ---
    title = f"{symbol} - {timeframe}".strip(" -") if symbol or timeframe else "Candlestick"
    fig.update_layout(
        title={"text": title, "font": {"size": 16, "color": "#e0e0e0"}},
        **_DARK_LAYOUT,
        height=620,
    )
    fig.update_yaxes(
        title_text=t("candlestick.price_axis"), title_font={"size": 11},
        gridcolor="rgba(255,255,255,0.06)", row=1, col=1,
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", row=2, col=1)
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.04)",
        showspikes=True, spikecolor="rgba(255,255,255,0.3)", spikethickness=1,
    )
    return fig
