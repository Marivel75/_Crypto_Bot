"""Page 2 — Analytics marché (market cap, dominance, gainers/losers, corrélations)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIClient
from frontend.components.candlestick import _DARK_LAYOUT
from frontend.i18n import t

logger = logging.getLogger(__name__)

_CORR_SYMBOLS = ("BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT")


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=120)
def _fetch_global() -> dict[str, Any] | None:
    return _get_client().fetch_market_global()


@st.cache_data(ttl=120)
def _fetch_top(limit: int = 50) -> dict[str, Any] | None:
    return _get_client().fetch_market_top(limit=limit)


@st.cache_data(ttl=300)
def _fetch_ohlcv_closes(symbol: str) -> list[float] | None:
    rows = _get_client().fetch_ohlcv(symbol, timeframe="1d", limit=90)
    if not rows:
        return None
    # API returns DESC; reverse to ASC for chronological order
    return [float(r["close"]) for r in reversed(rows) if r.get("close") is not None]


def _render_kpi_cards(global_data: dict[str, Any], top_data: dict[str, Any] | None) -> None:
    col1, col2, col3 = st.columns(3)

    with col1, st.container(border=True):
        mcap = global_data.get("market_cap_usd")
        if mcap is not None:
            st.metric(t("analytics.market_cap"), f"${float(mcap) / 1e12:.2f} T")
        else:
            st.metric(t("analytics.market_cap"), "-")
            st.caption(t("analytics.data_unavailable"))

    with col2, st.container(border=True):
        dominance = global_data.get("dominance") or []
        btc_dom = next((d["percentage"] for d in dominance if d.get("asset") == "btc"), None)
        if btc_dom is not None:
            st.metric(t("analytics.btc_dominance"), f"{btc_dom:.1f}%")
        else:
            st.metric(t("analytics.btc_dominance"), "-")
            st.caption(t("analytics.data_unavailable"))

    with col3, st.container(border=True):
        vol = global_data.get("volume_usd")
        if vol is not None:
            st.metric(t("analytics.volume_header"), f"${float(vol) / 1e9:.1f} B")
        else:
            st.metric(t("analytics.volume_header"), "-")
            st.caption(t("analytics.data_unavailable"))


def _render_heatmap(cryptos: list[dict[str, Any]]) -> None:
    if not cryptos:
        st.markdown(
            f"<div style='text-align:center;padding:2rem;color:#888'>{t('analytics.no_heatmap')}</div>",
            unsafe_allow_html=True,
        )
        return

    symbols = [c.get("symbol", "?") for c in cryptos if c.get("price_change_pct_24h") is not None]
    values = [float(c["price_change_pct_24h"]) for c in cryptos if c.get("price_change_pct_24h") is not None]

    if not symbols:
        return

    fig = go.Figure(go.Heatmap(
        z=[values],
        x=symbols,
        y=["24h"],
        colorscale="RdYlGn",
        zmid=0,
        text=[[f"{v:+.1f}%" for v in values]],
        texttemplate="%{text}",
        textfont={"size": 11},
        hoverongaps=False,
    ))
    fig.update_layout(
        height=200,
        title={"text": t("analytics.heatmap_chart_title"), "font": {"size": 13}},
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_movers(cryptos: list[dict[str, Any]]) -> None:
    col_gain, col_lose = st.columns(2)

    sorted_cryptos = sorted(
        [c for c in cryptos if c.get("price_change_pct_24h") is not None],
        key=lambda c: float(c["price_change_pct_24h"]),
        reverse=True,
    )
    gainers = sorted_cryptos[:5]
    losers = sorted_cryptos[-5:][::-1] if len(sorted_cryptos) >= 5 else []

    def _table(items: list[dict[str, Any]]) -> None:
        rows = [{
            t("analytics.col_crypto"): f"{item.get('name', '?')} ({item.get('symbol', '?')})",
            t("analytics.col_price"): f"${float(item.get('price') or 0):,.4f}",
            t("analytics.col_change_24h"): f"{float(item.get('price_change_pct_24h') or 0):+.2f}%",
            t("analytics.col_volume_24h"): f"${float(item.get('volume_24h') or 0):,.0f}",
        } for item in items]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with col_gain, st.container(border=True):
        st.markdown(f"### {t('analytics.gainers')}")
        if gainers:
            _table(gainers)
        else:
            st.markdown(f"<div style='text-align:center;color:#888'>{t('analytics.no_gainers')}</div>", unsafe_allow_html=True)

    with col_lose, st.container(border=True):
        st.markdown(f"### {t('analytics.losers')}")
        if losers:
            _table(losers)
        else:
            st.markdown(f"<div style='text-align:center;color:#888'>{t('analytics.no_losers')}</div>", unsafe_allow_html=True)


def _render_correlation() -> None:
    close_series: dict[str, list[float]] = {}
    for sym in _CORR_SYMBOLS:
        closes = _fetch_ohlcv_closes(sym)
        if closes and len(closes) > 5:
            close_series[sym.replace("/USDT", "")] = closes

    if len(close_series) < 2:
        with st.container(border=True):
            st.markdown(
                f"<div style='text-align:center;padding:2rem;color:#888'>{t('analytics.correlation_insufficient')}<br>"
                f"<small>{t('analytics.correlation_min_hint')}</small></div>",
                unsafe_allow_html=True,
            )
        return

    min_len = min(len(v) for v in close_series.values())
    aligned = {sym: vals[-min_len:] for sym, vals in close_series.items()}
    corr = pd.DataFrame(aligned).pct_change().dropna().corr()

    syms = list(corr.columns)
    z_vals = corr.values.tolist()

    fig = go.Figure(go.Heatmap(
        z=z_vals, x=syms, y=syms,
        colorscale="RdYlGn", zmin=-1, zmax=1, zmid=0,
        text=[[f"{v:.2f}" for v in row] for row in z_vals],
        texttemplate="%{text}", textfont={"size": 12},
    ))
    fig.update_layout(
        height=420,
        title={"text": t("analytics.correlation_chart_title"), "font": {"size": 13}},
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def page() -> None:
    st.header(t("analytics.header"))

    global_data = _fetch_global()
    top_data = _fetch_top(limit=50)

    if global_data is None and top_data is None:
        with st.container(border=True):
            st.error(t("analytics.backend_unavailable"))
            st.info(t("analytics.backend_hint"))
        return

    if global_data:
        _render_kpi_cards(global_data, top_data)
        st.divider()

    cryptos = (top_data or {}).get("cryptos") or []

    if cryptos:
        st.markdown(f"### {t('analytics.heatmap_title')}")
        with st.container(border=True):
            _render_heatmap(cryptos)
        st.divider()

        st.markdown(f"### {t('analytics.top_movers')}")
        _render_movers(cryptos)
        st.divider()

    st.markdown(f"### {t('analytics.correlation_title')}")
    with st.container(border=True):
        _render_correlation()


page()
