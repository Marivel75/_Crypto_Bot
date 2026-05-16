"""Page 3 — Exploration des signaux techniques."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st

from frontend.api_client import APIClient
from frontend.config import frontend_settings
from frontend.i18n import t
from frontend.utils import extract_symbols, extract_timeframes, fmt_ts


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=300)
def _fetch_available() -> tuple[list[str], list[str]]:
    data = _get_client().fetch_symbols(exchange=frontend_settings.default_exchange)
    if data:
        return extract_symbols(data), extract_timeframes(data)
    return frontend_settings.tracked_symbols, frontend_settings.timeframes


@st.cache_data(ttl=60)
def _fetch(symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]] | None:
    return _get_client().fetch_signals(symbol, timeframe, limit=limit, exchange=frontend_settings.default_exchange)


def _fmt(val: Any, decimals: int) -> float | None:
    if val is None:
        return None
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None


_SIGNAL_COLORS = {
    "buy":  "#22c55e",
    "sell": "#ef4444",
    "hold": "#94a3b8",
}

_SIGNAL_ICONS = {
    "buy":  "▲",
    "sell": "▼",
    "hold": "●",
}


def _render_signal_card(latest: dict) -> None:
    sig = latest.get("signal") or "hold"
    score = latest.get("signal_score")
    reasons: list[str] = latest.get("signal_reasons") or []
    color = _SIGNAL_COLORS.get(sig, "#94a3b8")
    icon = _SIGNAL_ICONS.get(sig, "●")
    score_str = f"{score:+.2f}" if score is not None else "—"

    reasons_html = "".join(
        f'<li style="margin:2px 0;font-size:0.85em;color:#cbd5e1">{r}</li>'
        for r in reasons
    ) if reasons else '<li style="color:#64748b;font-size:0.85em">Aucune règle déclenchée</li>'

    st.markdown(
        f"""
<div style="border:1px solid {color}55;border-radius:10px;padding:16px 20px;margin-bottom:18px;background:{color}0d">
  <div style="font-size:0.8em;color:#94a3b8;margin-bottom:6px">Signal actuel (dernière bougie)</div>
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
    <span style="font-size:1.8em;font-weight:700;color:{color}">{icon} {sig.upper()}</span>
    <span style="font-size:1.2em;color:{color};font-weight:600">{score_str}</span>
  </div>
  <ul style="margin:10px 0 0 0;padding-left:18px">
    {reasons_html}
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )


def _signal_badge(sig: str | None) -> str:
    s = sig or "hold"
    color = _SIGNAL_COLORS.get(s, "#94a3b8")
    icon = _SIGNAL_ICONS.get(s, "●")
    return f'<span style="color:{color};font-weight:700">{icon} {s.upper()}</span>'


def _render_help() -> None:
    with st.expander("Comment lire les signaux ?", expanded=False):
        st.markdown("""
**Le score composite** combine 4 indicateurs techniques pour chaque bougie :

| Indicateur | Règle | Vote |
|---|---|---|
| RSI | < 30 (survendu) | +1.0 |
| RSI | 30–45 (zone haussière) | +0.5 |
| RSI | 55–70 (zone baissière) | −0.5 |
| RSI | > 70 (surachat) | −1.0 |
| MACD | Croisement haussier | +1.0 |
| MACD | Croisement baissier | −1.0 |
| MACD | Ligne > signal (sans croisement) | +0.3 |
| Bollinger | Prix sous la bande inférieure | +1.0 |
| Bollinger | Prix au-dessus de la bande supérieure | −1.0 |
| SMA | Prix > SMA20 > SMA50 (tendance haussière) | +0.5 |
| SMA | Prix < SMA20 < SMA50 (tendance baissière) | −0.5 |

Le **score final** est la moyenne des votes des règles déclenchées, entre **−1.0** et **+1.0**.

| Score | Signal |
|---|---|
| > +0.30 | ▲ **BUY** — plusieurs indicateurs alignés à la hausse |
| entre −0.30 et +0.30 | ● **HOLD** — signaux contradictoires ou neutres |
| < −0.30 | ▼ **SELL** — plusieurs indicateurs alignés à la baisse |

> Ces signaux sont **indicatifs** et basés sur l'analyse technique uniquement. Ils ne constituent pas un conseil financier.
""")


def page() -> None:
    st.header(t("signals.header"))

    _render_help()

    available_symbols, available_timeframes = _fetch_available()

    col_sym, col_tf, col_lim = st.columns([2, 1, 1])
    with col_sym:
        symbol = st.selectbox(t("signals.symbol"), available_symbols)
    with col_tf:
        tf_default = available_timeframes.index("1d") if "1d" in available_timeframes else 0
        timeframe = st.selectbox(t("signals.timeframe"), available_timeframes, index=tf_default)
    with col_lim:
        limit = st.slider(t("signals.limit"), min_value=10, max_value=500, value=100, step=10)

    data = _fetch(symbol, timeframe, limit)

    if data is None:
        st.error(t("signals.no_data", symbol=symbol, timeframe=timeframe))
        return
    if not data:
        st.warning(t("signals.no_data", symbol=symbol, timeframe=timeframe))
        return

    # ── Carte signal actuel ───────────────────────────────────────────────────
    _render_signal_card(data[-1])

    # ── Répartition des signaux sur la période ────────────────────────────────
    counts: dict[str, int] = {"buy": 0, "sell": 0, "hold": 0}
    for row in data:
        sig = row.get("signal") or "hold"
        counts[sig] = counts.get(sig, 0) + 1

    c1, c2, c3 = st.columns(3)
    for col, key, label in [(c1, "buy", "Achats"), (c2, "sell", "Ventes"), (c3, "hold", "Neutres")]:
        color = _SIGNAL_COLORS[key]
        col.markdown(
            f'<div style="text-align:center;padding:8px;border:1px solid {color}44;border-radius:8px">'
            f'<div style="font-size:1.6em;font-weight:700;color:{color}">{counts[key]}</div>'
            f'<div style="font-size:0.8em;color:#94a3b8">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tableau ───────────────────────────────────────────────────────────────
    rows = []
    for row in data:
        sig = row.get("signal") or "hold"
        score = row.get("signal_score")
        rows.append({
            "Timestamp":   fmt_ts(row.get("timestamp")),
            "Signal":      sig.upper(),
            "Score":       _fmt(score, 3),
            "Close":       _fmt(row.get("close"), 2),
            "RSI(14)":     _fmt(row.get("rsi_14"), 2),
            "SMA(20)":     _fmt(row.get("sma_20"), 2),
            "SMA(50)":     _fmt(row.get("sma_50"), 2),
            "EMA(20)":     _fmt(row.get("ema_20"), 2),
            "MACD":        _fmt(row.get("macd_line"), 4),
            "MACD Signal": _fmt(row.get("macd_signal"), 4),
            "MACD Hist":   _fmt(row.get("macd_histogram"), 4),
            "BB Upper":    _fmt(row.get("bb_upper"), 2),
            "BB Middle":   _fmt(row.get("bb_middle"), 2),
            "BB Lower":    _fmt(row.get("bb_lower"), 2),
        })

    df = pd.DataFrame(rows)

    def _color_signal(val: str):
        mapping = {"BUY": "color: #22c55e; font-weight: 700",
                   "SELL": "color: #ef4444; font-weight: 700",
                   "HOLD": "color: #94a3b8"}
        return mapping.get(val, "")

    def _color_score(val):
        if val is None:
            return ""
        try:
            v = float(val)
            if v > 0.3:
                return "color: #22c55e"
            if v < -0.3:
                return "color: #ef4444"
            return "color: #94a3b8"
        except (TypeError, ValueError):
            return ""

    styled = (
        df.style
        .applymap(_color_signal, subset=["Signal"])
        .applymap(_color_score, subset=["Score"])
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.caption(f"{len(data)} lignes · {symbol} {timeframe}")


page()
