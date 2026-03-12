"""Page 5 — Performance des signaux.

Signal performance KPIs, cumulative P&L chart, per-symbol breakdown, signal history.
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.components.candlestick import _DARK_LAYOUT
from src.frontend.config import frontend_settings
from src.frontend.i18n import t

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=30)
def _fetch_performance() -> dict[str, Any] | None:
    """Return signal performance summary dict."""
    return _get_client().fetch_signal_performance()


@st.cache_data(ttl=30)
def _fetch_signals(symbol: str | None) -> list[dict[str, Any]] | None:
    """Return signals list, optionally filtered by symbol."""
    return _get_client().fetch_signals(symbol)


@st.cache_data(ttl=30)
def _fetch_signals_history(
    symbol: str | None,
    direction: str | None,
    limit: int = 100,
) -> dict[str, Any] | None:
    """Return paginated signal history with optional filters."""
    return _get_client().fetch_signals_history(symbol=symbol, direction=direction, limit=limit)


@st.cache_data(ttl=300)
def _fetch_system_metrics() -> dict[str, Any] | None:
    """Return system metrics: uptime, request count, error rate, DB size."""
    return _get_client().fetch_system_metrics()


def _format_confidence(value: Any) -> str:
    """Format a confidence score as a percentage string, safely."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "—"


def _perf_is_empty(perf: dict[str, Any]) -> bool:
    """Return True when the performance dict contains only None/zero values."""
    keys = ("total_signals", "evaluated_signals", "win_rate", "total_pnl")
    return all(perf.get(k) is None for k in keys)


def page() -> None:
    """Render the signal performance page."""
    st.header(t("performance.header"))

    perf = _fetch_performance()

    # API unreachable
    if perf is None:
        with st.container(border=True):
            st.error(t("performance.api_error"))
        return

    # API returned an empty payload (no signals evaluated yet)
    if _perf_is_empty(perf):
        with st.container(border=True):
            st.info(t("performance.no_data"))
        return

    # --- KPI summary cards ---
    with st.container(border=True):
        st.subheader(t("performance.global_metrics"))
        _render_kpis(perf)

    st.divider()

    # --- Win-rate gauge (only when meaningful) ---
    win_rate = float(perf.get("win_rate") or 0)
    if win_rate > 0:
        with st.container(border=True):
            st.subheader(t("performance.win_rate"))
            _render_win_rate_gauge(win_rate)
        st.divider()

    # --- Cumulative P&L chart ---
    signals_all = _fetch_signals(None)

    with st.container(border=True):
        st.subheader(t("performance.cumulative_pnl"))
        _render_cumulative_pnl(signals_all)

    st.divider()

    # --- Per-symbol and per-timeframe breakdown tables ---
    col_left, col_right = st.columns(2)
    with col_left, st.container(border=True):
        st.subheader(t("performance.per_crypto"))
        _render_per_symbol_table(signals_all)

    with col_right, st.container(border=True):
        st.subheader(t("performance.per_timeframe"))
        _render_per_timeframe_table(signals_all)

    st.divider()

    # --- System metrics (Semaine 3) ---
    metrics = _fetch_system_metrics()
    if metrics:
        with st.container(border=True):
            st.subheader(t("performance.system_metrics"))
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                uptime = metrics.get("uptime_hours", "—")
                st.metric(t("performance.uptime"), f"{uptime}h" if isinstance(uptime, (int, float)) else uptime)
            with col2:
                requests = metrics.get("request_count", "—")
                st.metric(t("performance.request_count"), requests)
            with col3:
                error_rate = metrics.get("error_rate", 0.0)
                st.metric(t("performance.error_rate"), f"{float(error_rate):.2f}%")
            with col4:
                db_size = metrics.get("db_size_mb", "—")
                st.metric(t("performance.db_size"), f"{db_size}MB" if isinstance(db_size, (int, float)) else db_size)

        st.divider()

    # --- Filterable signal history table ---
    with st.container(border=True):
        st.subheader(t("performance.signal_history"))
        _render_signal_history_section()


def _render_kpis(perf: dict[str, Any]) -> None:
    """Render summary KPI metrics: signal counts, win rate, and total simulated P&L."""
    # Use `or 0` to coerce None (missing JSON field) to a safe default
    total_signals = int(perf.get("total_signals") or 0)
    evaluated = int(perf.get("evaluated_signals") or 0)
    win_rate = float(perf.get("win_rate") or 0)
    total_pnl = perf.get("total_pnl")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t("performance.signals_emitted"), total_signals)
    with col2:
        st.metric(t("performance.evaluated"), evaluated)
    with col3:
        st.metric(t("performance.win_rate"), f"{win_rate:.1f}%")
    with col4:
        # total_pnl may be legitimately None when no signals have been closed yet
        if total_pnl is not None:
            try:
                pnl_value = float(total_pnl)
            except (TypeError, ValueError):
                pnl_value = 0.0
            st.metric(t("performance.simulated_pnl"), f"${pnl_value:+,.2f}")
        else:
            st.metric(t("performance.simulated_pnl"), "—")


def _render_win_rate_gauge(win_rate: float) -> None:
    """Render a Plotly gauge chart showing the win rate percentage."""
    # Color thresholds: green >= 60 %, yellow >= 50 %, red below
    color = "#26a69a" if win_rate >= 60 else "#ffeb3b" if win_rate >= 50 else "#ef5350"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=win_rate,
            title={"text": t("performance.win_rate_gauge"), "font": {"size": 16, "color": "#fafafa"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#fafafa"},
                "bar": {"color": color},
                "bgcolor": "#161b22",
                "steps": [
                    {"range": [0, 40], "color": "#b71c1c"},
                    {"range": [40, 55], "color": "#f9a825"},
                    {"range": [55, 100], "color": "#1b5e20"},
                ],
                "threshold": {
                    "line": {"color": "#fafafa", "width": 3},
                    "thickness": 0.75,
                    "value": win_rate,
                },
            },
            number={"suffix": "%", "font": {"color": "#fafafa"}},
        )
    )
    fig.update_layout(height=280, **_DARK_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def _render_cumulative_pnl(signals: list[dict[str, Any]] | None) -> None:
    """Render a cumulative P&L line chart built from individual signal outcomes."""
    if not signals:
        st.info(t("performance.no_signals_pnl"))
        return

    # Keep only signals that have been evaluated (pnl or correctness recorded)
    with_pnl = [s for s in signals if s.get("pnl_simulated") is not None or s.get("was_correct") is not None]
    if not with_pnl:
        st.info(t("performance.no_evaluated_pnl"))
        return

    # Sort chronologically before accumulating
    sorted_signals = sorted(with_pnl, key=lambda s: s.get("created_at") or s.get("timestamp") or "")
    cumulative = 0.0
    dates: list[str] = []
    values: list[float] = []

    for s in sorted_signals:
        pnl = s.get("pnl_simulated")
        if pnl is not None:
            # Prefer exact simulated P&L when available
            cumulative += float(pnl)
        elif s.get("was_correct") is True:
            # Fallback: +1 unit per correct signal, -1 per incorrect
            cumulative += 1.0
        elif s.get("was_correct") is False:
            cumulative -= 1.0
        dates.append(s.get("created_at") or s.get("timestamp") or "")
        values.append(cumulative)

    if not dates:
        st.info(t("performance.insufficient_data"))
        return

    # Chart color reflects whether the strategy is net positive or negative
    final_color = "#26a69a" if values[-1] >= 0 else "#ef5350"
    fill_color = "rgba(38,166,154,0.1)" if values[-1] >= 0 else "rgba(239,83,80,0.1)"

    fig = go.Figure(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines+markers",
            name=t("performance.chart_cumulative"),
            line={"color": final_color, "width": 2},
            fill="tozeroy",
            fillcolor=fill_color,
        )
    )
    fig.update_layout(
        xaxis_title=t("performance.chart_date"),
        yaxis_title=t("performance.chart_pnl"),
        height=350,
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_per_symbol_table(signals: list[dict[str, Any]] | None) -> None:
    """Render an aggregated performance table grouped by trading symbol."""
    if not signals:
        st.info(t("performance.no_crypto_data"))
        return

    # Accumulate counts and P&L per symbol
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "correct": 0, "pnl": 0.0})

    for s in signals:
        sym = s.get("symbol") or "?"
        stats[sym]["total"] += 1
        if s.get("was_correct") is True:
            stats[sym]["correct"] += 1
        pnl = s.get("pnl_simulated")
        if pnl is not None:
            stats[sym]["pnl"] += float(pnl)

    rows = []
    for sym, sym_data in sorted(stats.items()):
        wr = (sym_data["correct"] / sym_data["total"] * 100) if sym_data["total"] > 0 else 0.0
        rows.append(
            {
                t("performance.col_crypto"): sym,
                t("performance.col_signals"): sym_data["total"],
                t("performance.col_win_rate"): f"{wr:.1f}%",
                t("performance.col_simulated_pnl"): f"${sym_data['pnl']:+,.2f}",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_per_timeframe_table(signals: list[dict[str, Any]] | None) -> None:
    """Render an aggregated performance table grouped by timeframe."""
    if not signals:
        st.info(t("performance.no_tf_data"))
        return

    # Accumulate counts and P&L per timeframe
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "correct": 0, "pnl": 0.0})

    for s in signals:
        tf = s.get("timeframe_primary") or "?"
        stats[tf]["total"] += 1
        if s.get("was_correct") is True:
            stats[tf]["correct"] += 1
        pnl = s.get("pnl_simulated")
        if pnl is not None:
            stats[tf]["pnl"] += float(pnl)

    rows = []
    for tf, tf_data in sorted(stats.items()):
        wr = (tf_data["correct"] / tf_data["total"] * 100) if tf_data["total"] > 0 else 0.0
        rows.append(
            {
                t("performance.col_timeframe"): tf,
                t("performance.col_signals"): tf_data["total"],
                t("performance.col_win_rate"): f"{wr:.1f}%",
                t("performance.col_simulated_pnl"): f"${tf_data['pnl']:+,.2f}",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_signal_history_section() -> None:
    """Render a filterable, exportable signal history table."""
    # Filter controls placed side-by-side
    all_label = t("performance.filter_all")
    col_sym, col_dir = st.columns(2)
    with col_sym:
        symbol_filter = st.selectbox(
            t("performance.filter_crypto"),
            [all_label, *frontend_settings.tracked_symbols],
            key="perf_sym_filter",
        )
    with col_dir:
        direction_filter = st.selectbox(
            t("performance.filter_direction"),
            [all_label, "BUY", "SELL", "HOLD"],
            key="perf_dir_filter",
        )

    sym = None if symbol_filter == all_label else symbol_filter
    signals = _fetch_signals(sym)

    if signals is None:
        st.error(t("performance.signals_api_error"))
        return

    if not signals:
        st.info(t("performance.no_signals_period"))
        return

    # Apply direction filter client-side (API may not support it)
    if direction_filter != all_label:
        signals = [s for s in signals if str(s.get("signal_type") or "").upper() == direction_filter]

    if not signals:
        st.info(t("performance.no_signals_filter"))
        return

    yes_label = t("performance.yes")
    no_label = t("performance.no")

    # Build display rows — use `or` guards so None fields fall back to display placeholders
    rows = [
        {
            t("performance.col_date"): s.get("created_at") or s.get("timestamp") or "—",
            t("performance.col_crypto"): s.get("symbol") or "?",
            t("performance.col_direction"): s.get("signal_type") or "?",
            t("performance.col_confidence"): _format_confidence(s.get("confidence_score")),
            t("performance.col_timeframe"): s.get("timeframe_primary") or "—",
            t("performance.col_leverage"): f"{s['leverage_suggested']}x" if s.get("leverage_suggested") else "—",
            t("performance.col_rules"): ", ".join(s.get("rules_triggered") or []) or "—",
            t("performance.col_correct"): (
                yes_label if s.get("was_correct") is True else no_label if s.get("was_correct") is False else "—"
            ),
            # pnl_simulated checked explicitly to avoid formatting a None value
            t("performance.col_pnl"): (
                f"${float(s.get('pnl_simulated') or 0):+,.2f}" if s.get("pnl_simulated") is not None else "—"
            ),
        }
        for s in sorted(
            signals,
            key=lambda x: x.get("created_at") or x.get("timestamp") or "",
            reverse=True,
        )
    ]

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # CSV export button
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        t("performance.export_csv"),
        data=csv_data,
        file_name="signaux.csv",
        mime="text/csv",
    )


page()
