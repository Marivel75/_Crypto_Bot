"""Page 6 — Paper Trading : simulation de trades sur capital fictif."""

from __future__ import annotations

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
from frontend.config import frontend_settings
from frontend.utils import extract_symbols, fmt_ts

# ── Constantes ────────────────────────────────────────────────────────────────

_GREEN = "#22c55e"
_RED = "#ef4444"
_SLATE = "#94a3b8"

_PNL_HELP = "P&L = (prix sortie − prix entrée) × quantité"


# ── Client & données cachées ──────────────────────────────────────────────────

@st.cache_resource
def _client() -> APIClient:
    return APIClient()


@st.cache_data(ttl=300)
def _available_symbols() -> list[str]:
    data = _client().fetch_symbols()
    if data:
        return extract_symbols(data)
    return frontend_settings.tracked_symbols


@st.cache_data(ttl=30)
def _portfolios() -> list[dict[str, Any]]:
    return _client().list_portfolios() or []


# ── Helpers visuels ───────────────────────────────────────────────────────────

def _pnl_color(val: float | None) -> str:
    if val is None:
        return _SLATE
    return _GREEN if val >= 0 else _RED


def _pnl_str(val: float | None, suffix: str = " USDT") -> str:
    if val is None:
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:,.4f}{suffix}"


def _metric_pnl(label: str, val: float | None, suffix: str = " USDT") -> None:
    color = _pnl_color(val)
    text = _pnl_str(val, suffix)
    st.markdown(
        f"""
<div style="padding:12px 16px;border:1px solid {color}44;border-radius:10px;background:{color}0d;text-align:center">
  <div style="font-size:0.75em;color:{_SLATE};margin-bottom:4px">{label}</div>
  <div style="font-size:1.3em;font-weight:700;color:{color}">{text}</div>
</div>""",
        unsafe_allow_html=True,
    )


# ── Section : sélecteur / créateur de portefeuille ───────────────────────────

def _section_portfolio_selector() -> str | None:
    """Affiche le sélecteur et le formulaire de création. Retourne le portfolio_id sélectionné."""
    portfolios = _portfolios()

    st.subheader("Portefeuille")

    col_sel, col_btn = st.columns([4, 1])

    if portfolios:
        options = {f"{p['name']} ({p['cash']:,.2f} USDT)": p["id"] for p in portfolios}
        with col_sel:
            chosen_label = st.selectbox("Choisir un portefeuille", list(options.keys()), label_visibility="collapsed")
        selected_id = options[chosen_label]
    else:
        with col_sel:
            st.info("Aucun portefeuille — créez-en un ci-dessous.")
        selected_id = None

    with col_btn:
        if st.button("＋ Nouveau", use_container_width=True):
            st.session_state["show_create_form"] = not st.session_state.get("show_create_form", False)

    if st.session_state.get("show_create_form", False):
        with st.form("create_portfolio_form", clear_on_submit=True):
            st.markdown("**Nouveau portefeuille fictif**")
            name = st.text_input("Nom", placeholder="Ex : Stratégie BTC Q2 2026")
            capital = st.number_input("Capital de départ (USDT)", min_value=1.0, value=10_000.0, step=500.0)
            submitted = st.form_submit_button("Créer")
            if submitted:
                if not name.strip():
                    st.error("Le nom est requis.")
                else:
                    result = _client().create_portfolio(name.strip(), capital)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(f"Portefeuille « {result['name']} » créé avec {capital:,.2f} USDT.")
                        _portfolios.clear()
                        st.session_state["show_create_form"] = False
                        st.rerun()

    return selected_id


# ── Section : résumé métriques ────────────────────────────────────────────────

def _section_summary(summary: dict[str, Any]) -> None:
    m = summary["metrics"]
    p = summary["portfolio"]

    st.subheader("Résumé")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Capital total", f"{m['total_capital']:,.2f} USDT",
                  delta=f"{m['total_capital'] - p['initial_capital']:+,.2f}")
    with c2:
        _metric_pnl("P&L réalisé", m["total_realized_pnl"])
    with c3:
        _metric_pnl("P&L latent", m["latent_pnl"])
    with c4:
        wr = m["win_rate"]
        color = _GREEN if wr >= 50 else _RED
        st.markdown(
            f"""<div style="padding:12px 16px;border:1px solid {color}44;border-radius:10px;
background:{color}0d;text-align:center">
  <div style="font-size:0.75em;color:{_SLATE};margin-bottom:4px">Win rate</div>
  <div style="font-size:1.3em;font-weight:700;color:{color}">{wr:.1f} %</div>
  <div style="font-size:0.7em;color:{_SLATE}">{m['total_closed_trades']} trades fermés</div>
</div>""",
            unsafe_allow_html=True,
        )

    # Cash disponible (petite info complémentaire)
    st.caption(f"Cash disponible : **{p['cash']:,.4f} USDT** · Capital initial : {p['initial_capital']:,.2f} USDT")


# ── Section : positions ouvertes ──────────────────────────────────────────────

def _section_open_positions(summary: dict[str, Any], portfolio_id: str) -> None:
    positions = summary.get("open_positions", [])

    st.subheader(f"Positions ouvertes ({len(positions)})")

    if not positions:
        st.info("Aucune position ouverte.")
        return

    for pos in positions:
        pnl = pos["pnl_latent"]
        pct = pos["pnl_latent_pct"]
        color = _pnl_color(pnl)
        sign = "+" if pnl >= 0 else ""

        col_info, col_pnl, col_btn = st.columns([4, 3, 1])
        with col_info:
            st.markdown(
                f"**{pos['symbol']}** &nbsp;·&nbsp; {pos['quantity']:.6g} unités"
                f" &nbsp;·&nbsp; Entrée : **{pos['entry_price']:,.4f}** USDT"
                f" &nbsp;·&nbsp; Actuel : **{pos['current_price']:,.4f}** USDT"
                f"<br><small style='color:{_SLATE}'>Source : {pos['signal_source']}"
                f" &nbsp;·&nbsp; {fmt_ts(pos['entry_time'])}</small>",
                unsafe_allow_html=True,
            )
        with col_pnl:
            st.markdown(
                f"<div style='text-align:center;padding:4px 8px;border-radius:6px;"
                f"border:1px solid {color}44;background:{color}0d'>"
                f"<span style='color:{color};font-weight:700;font-size:1.1em'>"
                f"{sign}{pnl:,.4f} USDT</span><br>"
                f"<span style='color:{color};font-size:0.85em'>{sign}{pct:.2f} %</span></div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Fermer", key=f"close_{pos['id']}", use_container_width=True):
                result = _client().close_order(pos["id"])
                if "error" in result:
                    st.error(result["error"])
                else:
                    closed_pnl = result.get("pnl", 0) or 0
                    st.success(f"{pos['symbol']} fermé — P&L : {_pnl_str(closed_pnl)}")
                    st.rerun()

        st.divider()


# ── Section : passer un ordre ─────────────────────────────────────────────────

def _section_place_order(portfolio_id: str, cash: float) -> None:
    st.subheader("Passer un ordre BUY")

    symbols = _available_symbols()

    with st.form("place_order_form", clear_on_submit=True):
        symbol = st.selectbox("Actif", symbols)

        mode = st.radio("Saisie par", ["Quantité (unités)", "Montant (USDT)"], horizontal=True)

        if mode == "Quantité (unités)":
            qty = st.number_input("Quantité", min_value=0.0001, value=0.01, step=0.001, format="%.6f")
            amount = None
        else:
            amount = st.number_input("Montant (USDT)", min_value=1.0, value=100.0, step=10.0)
            qty = None

        st.caption(f"Cash disponible : **{cash:,.4f} USDT**")

        submitted = st.form_submit_button("Placer l'ordre", use_container_width=True)
        if submitted:
            result = _client().place_order(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=qty,
                amount_usdt=amount,
            )
            if "error" in result:
                st.error(result["error"])
            else:
                entry = result.get("entry_price", 0)
                q = result.get("quantity", 0)
                st.success(f"Ordre BUY placé : {q:.6g} {symbol} @ {entry:,.4f} USDT")
                st.rerun()


# ── Section : historique des trades ──────────────────────────────────────────

def _section_history(summary: dict[str, Any]) -> None:
    closed = summary.get("closed_trades", [])

    st.subheader(f"Historique ({len(closed)} trades fermés)")

    if not closed:
        st.info("Aucun trade fermé pour l'instant.")
        return

    rows = []
    for t in closed:
        pnl = t.get("pnl")
        pct = t.get("pnl_pct")
        rows.append({
            "Symbole":      t["symbol"],
            "Quantité":     round(t["quantity"], 6),
            "Entrée":       t["entry_price"],
            "Sortie":       t.get("exit_price"),
            "P&L (USDT)":   round(pnl, 4) if pnl is not None else None,
            "P&L (%)":      round(pct, 2) if pct is not None else None,
            "Source":       t["signal_source"],
            "Ouverture":    fmt_ts(t["entry_time"]),
            "Fermeture":    fmt_ts(t.get("exit_time")),
        })

    df = pd.DataFrame(rows)

    def _color_pnl(val):
        if val is None or pd.isna(val):
            return ""
        return f"color: {_GREEN}; font-weight:600" if val >= 0 else f"color: {_RED}; font-weight:600"

    styled = df.style.applymap(_color_pnl, subset=["P&L (USDT)", "P&L (%)"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ── Section : courbe de performance ──────────────────────────────────────────

def _section_performance_chart(summary: dict[str, Any]) -> None:
    closed = summary.get("closed_trades", [])
    initial = summary["portfolio"]["initial_capital"]

    if not closed:
        return

    trades_sorted = sorted(
        [t for t in closed if t.get("exit_time") and t.get("pnl") is not None],
        key=lambda t: t["exit_time"],
    )

    if not trades_sorted:
        return

    st.subheader("Courbe de performance")

    dates = [fmt_ts(summary["portfolio"]["created_at"])]
    capital = [initial]
    running = initial

    for t in trades_sorted:
        running += t["pnl"]
        dates.append(fmt_ts(t["exit_time"]))
        capital.append(round(running, 4))

    final_color = _GREEN if capital[-1] >= initial else _RED

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=capital,
        mode="lines+markers",
        line=dict(color=final_color, width=2),
        marker=dict(size=6, color=final_color),
        fill="tozeroy",
        fillcolor=f"{final_color}22",
        hovertemplate="%{x}<br>Capital : %{y:,.4f} USDT<extra></extra>",
    ))
    fig.add_hline(
        y=initial,
        line_dash="dash",
        line_color=_SLATE,
        annotation_text=f"Capital initial : {initial:,.2f}",
        annotation_position="bottom right",
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Capital (USDT)",
        height=320,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Page principale ───────────────────────────────────────────────────────────

def page() -> None:
    st.header("Paper Trading")
    st.caption("Simulez des trades sur capital fictif sans risque réel.")

    # ── Sélecteur de portefeuille ─────────────────────────────────────────────
    portfolio_id = _section_portfolio_selector()

    if portfolio_id is None:
        return

    st.markdown("---")

    # ── Chargement du résumé (pas de cache — données mutables) ───────────────
    summary = _client().get_portfolio_summary(portfolio_id)
    if summary is None:
        st.error("Impossible de charger le portefeuille.")
        return

    # ── Résumé métriques ──────────────────────────────────────────────────────
    _section_summary(summary)

    st.markdown("---")

    # ── Positions ouvertes | Passer un ordre ─────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        _section_open_positions(summary, portfolio_id)

    with col_right:
        _section_place_order(portfolio_id, cash=summary["portfolio"]["cash"])

    st.markdown("---")

    # ── Historique ────────────────────────────────────────────────────────────
    _section_history(summary)

    # ── Courbe de performance ─────────────────────────────────────────────────
    _section_performance_chart(summary)


page()
