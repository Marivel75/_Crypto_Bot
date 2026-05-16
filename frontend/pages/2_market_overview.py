"""Page 2 — Analytics marché (market cap, dominance, gainers/losers, corrélations)."""

from __future__ import annotations

import logging
import math
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
from frontend.config import frontend_settings
from frontend.i18n import t

logger = logging.getLogger(__name__)

_CORR_SYMBOLS = ("BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT")


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=300)
def _fetch_fear_greed() -> dict[str, Any] | None:
    return _get_client().fetch_fear_greed()


@st.cache_data(ttl=120)
def _fetch_global() -> dict[str, Any] | None:
    return _get_client().fetch_market_global()


@st.cache_data(ttl=120)
def _fetch_top(limit: int = 50) -> dict[str, Any] | None:
    return _get_client().fetch_market_top(limit=limit)


@st.cache_data(ttl=120)
def _fetch_history(limit: int = 90) -> list[dict[str, Any]] | None:
    return _get_client().fetch_market_history(limit=limit)


@st.cache_data(ttl=300)
def _fetch_ohlcv_closes(symbol: str) -> list[float] | None:
    rows = _get_client().fetch_ohlcv(symbol, timeframe="1d", limit=90, exchange=frontend_settings.default_exchange)
    if not rows:
        return None
    return [float(r["close"]) for r in reversed(rows) if r.get("close") is not None]


def _render_fear_greed(data: dict[str, Any]) -> None:
    value = data.get("value", 0)
    classification = data.get("classification", "")
    timestamp = (data.get("timestamp") or "")[:10]

    if value <= 24:
        color = "#ef4444"
    elif value <= 44:
        color = "#f97316"
    elif value <= 55:
        color = "#eab308"
    elif value <= 74:
        color = "#84cc16"
    else:
        color = "#22c55e"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"font": {"size": 48, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#8b949e"},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#161b22",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 25],  "color": "#450a0a"},
                {"range": [25, 45], "color": "#431407"},
                {"range": [45, 55], "color": "#422006"},
                {"range": [55, 75], "color": "#1a2e05"},
                {"range": [75, 100], "color": "#052e16"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.85,
                "value": value,
            },
        },
        title={"text": f"{t('fng.title')}<br><span style='font-size:0.8em;color:#8b949e'>{t('fng.subtitle')}</span>"},
    ))
    fig.update_layout(
        height=280,
        margin={"t": 60, "b": 0, "l": 20, "r": 20},
        paper_bgcolor="#0d1117",
        font={"color": "#e6edf3"},
    )

    col_gauge, col_label = st.columns([2, 1])
    with col_gauge:
        st.plotly_chart(fig, use_container_width=True)
    with col_label:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:1.8em;font-weight:700;color:{color}">{classification}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.85em;color:#8b949e;margin-top:4px">{timestamp}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.78em;color:#8b949e;margin-top:12px">'
            f'0–24 Peur Extrême · 25–44 Peur<br>'
            f'45–55 Neutre · 56–74 Avidité<br>'
            f'75–100 Avidité Extrême</div>',
            unsafe_allow_html=True,
        )
        with st.expander("C'est quoi ?", expanded=False):
            st.caption(
                "Le **Fear & Greed Index** mesure le sentiment global du marché crypto "
                "sur une échelle de 0 (peur extrême) à 100 (avidité extrême). "
                "Il est calculé par [alternative.me](https://alternative.me/crypto/fear-and-greed-index/) "
                "à partir du volume, de la volatilité, des réseaux sociaux et des tendances de recherche. "
                "Un marché en peur extrême peut signaler une opportunité d'achat ; "
                "l'avidité extrême peut précéder une correction."
            )


def _render_kpi_cards(global_data: dict[str, Any], top_data: dict[str, Any] | None) -> None:
    col1, col2, col3 = st.columns(3)

    with col1, st.container(border=True):
        mcap = global_data.get("market_cap_usd")
        if mcap is not None:
            st.metric(
                t("analytics.market_cap"),
                f"${float(mcap) / 1e12:.2f} T",
                help=(
                    "**Capitalisation totale du marché crypto** (en trillions de dollars).\n\n"
                    "Somme de la valeur de marché de toutes les cryptomonnaies en circulation "
                    "(prix × offre circulante). "
                    "T = trillion = 1 000 milliards. "
                    "Source : CoinGecko."
                ),
            )
        else:
            st.metric(t("analytics.market_cap"), "-")
            st.caption(t("analytics.data_unavailable"))

    with col2, st.container(border=True):
        dominance = global_data.get("dominance") or []
        btc_dom = next((d["percentage"] for d in dominance if d.get("asset") == "btc"), None)
        if btc_dom is not None:
            st.metric(
                t("analytics.btc_dominance"),
                f"{btc_dom:.1f}%",
                help=(
                    "**Dominance Bitcoin** : part de Bitcoin dans la capitalisation totale "
                    "du marché crypto.\n\n"
                    "Une dominance élevée (> 60 %) signale que les investisseurs privilégient "
                    "BTC par rapport aux altcoins. Une dominance en baisse peut indiquer "
                    "une rotation vers les altcoins (altseason)."
                ),
            )
        else:
            st.metric(t("analytics.btc_dominance"), "-")
            st.caption(t("analytics.data_unavailable"))

    with col3, st.container(border=True):
        vol = global_data.get("volume_usd")
        if vol is not None:
            st.metric(
                t("analytics.volume_header"),
                f"${float(vol) / 1e9:.1f} B",
                help=(
                    "**Volume d'échange sur 24h** (en milliards de dollars).\n\n"
                    "Somme de toutes les transactions enregistrées sur l'ensemble des exchanges "
                    "au cours des dernières 24 heures. "
                    "Un volume élevé confirme la force d'un mouvement de prix ; "
                    "un volume faible suggère un manque de conviction. "
                    "B = billion = 1 milliard."
                ),
            )
        else:
            st.metric(t("analytics.volume_header"), "-")
            st.caption(t("analytics.data_unavailable"))


def _render_market_evolution(global_data: dict[str, Any], history: list[dict[str, Any]] | None) -> None:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        with st.container(border=True):
            st.markdown("### Capitalisation totale")
            st.caption("Évolution de la capitalisation totale du marché crypto en trillions de dollars.")
            if history:
                timestamps = [r["timestamp"] for r in history]
                caps = [r["market_cap_usd"] / 1e12 for r in history]
                fig = go.Figure(go.Scatter(
                    x=timestamps,
                    y=caps,
                    mode="lines",
                    line={"color": "#3b82f6", "width": 2},
                    fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.1)",
                    hovertemplate="%{x}<br>$%{y:.2f} T<extra></extra>",
                ))
                fig.update_layout(
                    height=300,
                    xaxis_title=None,
                    yaxis_title="Market Cap (T$)",
                    **_DARK_LAYOUT,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Données historiques indisponibles.")

    with col_right:
        with st.container(border=True):
            st.markdown("### Dominance")
            st.caption("Répartition de la capitalisation entre BTC, ETH et les autres cryptos.")
            dominance_raw = global_data.get("dominance") or []
            if dominance_raw:
                labels = []
                values = []
                autres = 0.0
                for item in dominance_raw:
                    asset = item.get("asset", "").upper()
                    pct = float(item.get("percentage", 0))
                    if asset == "BTC":
                        labels.append("BTC")
                        values.append(pct)
                    elif asset == "ETH":
                        labels.append("ETH")
                        values.append(pct)
                    else:
                        autres += pct
                if autres > 0:
                    labels.append("Autres")
                    values.append(autres)
                colors = []
                for lbl in labels:
                    if lbl == "BTC":
                        colors.append("#f7931a")
                    elif lbl == "ETH":
                        colors.append("#627eea")
                    else:
                        colors.append("#4a5568")
                fig = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.55,
                    marker={"colors": colors},
                    textinfo="label+percent",
                    hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
                ))
                fig.update_layout(
                    height=300,
                    showlegend=False,
                    **_DARK_LAYOUT,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Données de dominance indisponibles.")


def _render_top20_table(cryptos: list[dict[str, Any]], global_data: dict[str, Any]) -> None:
    total_mcap = global_data.get("market_cap_usd")
    top20 = cryptos[:20]
    rows = []
    for c in top20:
        mcap = c.get("market_cap")
        dom = (float(mcap) / float(total_mcap) * 100) if (mcap and total_mcap) else None
        rows.append({
            "Rang": c.get("rank", "-"),
            "Crypto": f"{c.get('name', '?')} ({(c.get('symbol') or '?').upper()})",
            "Prix ($)": float(c.get("price") or 0),
            "Var. 24h (%)": float(c.get("price_change_pct_24h") or 0),
            "Market Cap ($)": float(mcap or 0),
            "Volume 24h ($)": float(c.get("volume_24h") or 0),
            "Dominance (%)": round(dom, 2) if dom is not None else None,
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Prix ($)": st.column_config.NumberColumn(format="$%.4f"),
            "Var. 24h (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Market Cap ($)": st.column_config.NumberColumn(format="$%.0f"),
            "Volume 24h ($)": st.column_config.NumberColumn(format="$%.0f"),
            "Dominance (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


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


def _render_scatter_liquidity(cryptos: list[dict[str, Any]]) -> None:
    filtered = [
        c for c in cryptos
        if c.get("market_cap") and float(c["market_cap"]) > 0
        and c.get("volume_24h") and float(c["volume_24h"]) > 0
    ]
    if not filtered:
        st.caption("Données insuffisantes pour le scatter.")
        return

    market_caps = [float(c["market_cap"]) for c in filtered]
    volumes = [float(c["volume_24h"]) for c in filtered]
    rotation = [v / m * 100 for v, m in zip(volumes, market_caps)]
    changes = [float(c.get("price_change_pct_24h") or 0) for c in filtered]
    symbols = [(c.get("symbol") or "?").upper() for c in filtered]

    raw_sizes = [math.sqrt(m) for m in market_caps]
    max_size = max(raw_sizes) if raw_sizes else 1
    sizes = [max(4.0, r / max_size * 40) for r in raw_sizes]

    fig = go.Figure(go.Scatter(
        x=market_caps,
        y=rotation,
        mode="markers+text",
        text=symbols,
        textposition="top center",
        textfont={"size": 9},
        marker={
            "size": sizes,
            "color": changes,
            "colorscale": "RdYlGn",
            "cmid": 0,
            "showscale": True,
            "colorbar": {"title": "Var. 24h (%)"},
        },
        hovertemplate="<b>%{text}</b><br>Market Cap: $%{x:,.0f}<br>Rotation: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        height=480,
        xaxis={
            "type": "log",
            "title": "Market Cap ($, log)",
        },
        yaxis={"title": "Volume 24h / Market Cap (%)"},
        **_DARK_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Le ratio Volume/Market Cap mesure la liquidité relative : "
        "un ratio élevé indique une forte activité d'échange par rapport à la taille de la crypto."
    )


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

    fng_data = _fetch_fear_greed()
    global_data = _fetch_global()
    top_data = _fetch_top(limit=50)
    history = _fetch_history(limit=90)

    if fng_data:
        with st.container(border=True):
            _render_fear_greed(fng_data)
        st.divider()

    if global_data is None and top_data is None:
        with st.container(border=True):
            st.error(t("analytics.backend_unavailable"))
            st.info(t("analytics.backend_hint"))
        return

    if global_data:
        _render_kpi_cards(global_data, top_data)
        st.divider()

    if global_data:
        st.markdown("### Évolution du marché")
        st.caption("Capitalisation totale et répartition de la dominance entre les principales cryptomonnaies.")
        _render_market_evolution(global_data, history)
        st.divider()

    cryptos = (top_data or {}).get("cryptos") or []

    if cryptos:
        st.markdown(f"### {t('analytics.heatmap_title')}")
        st.caption(
            "Variation de prix sur 24h pour chaque crypto du Top 50. "
            "Vert = hausse, rouge = baisse. L'intensité de la couleur reflète l'amplitude de la variation."
        )
        with st.container(border=True):
            _render_heatmap(cryptos)
        st.divider()

        st.markdown(f"### {t('analytics.top_movers')}")
        st.caption(
            "Les 5 cryptos ayant le plus progressé (gainers) et le plus reculé (losers) "
            "en 24h parmi le Top 50 par capitalisation."
        )
        _render_movers(cryptos)
        st.divider()

        if global_data:
            st.markdown("### Top 20 — Vue détaillée")
            st.caption(
                "Tableau enrichi des 20 premières cryptomonnaies par capitalisation, "
                "avec la dominance relative calculée sur le marché total."
            )
            with st.container(border=True):
                _render_top20_table(cryptos, global_data)
            st.divider()

        st.markdown("### Liquidité relative (bubble chart)")
        with st.container(border=True):
            _render_scatter_liquidity(cryptos)
        st.divider()

    st.markdown(f"### {t('analytics.correlation_title')}")
    st.caption(
        "Corrélation des rendements journaliers (close-to-close) sur les 90 derniers jours. "
        "1 = parfaitement corrélés (bougent ensemble), -1 = inversement corrélés, 0 = indépendants. "
        "Une forte corrélation entre altcoins et BTC est normale en période de marché baissier."
    )
    with st.container(border=True):
        _render_correlation()


page()
