"""Page 3 — Portfolio & Chatbot (Aleksandar, Investisseur).

Portfolio table with P&L + add/edit/delete position form + watchlist + chatbot.
Auth-gated.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.components.chatbot import render_chatbot
from src.frontend.components.portfolio_charts import (
    render_portfolio_history_chart,
    render_portfolio_pie,
)
from src.frontend.config import frontend_settings
from src.frontend.i18n import t

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_client() -> APIClient:
    return APIClient()


_client = _get_client()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    """Convert value to float safely, returning fallback on None or invalid input."""
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def page() -> None:
    """Render the portfolio page."""
    st.header(t("portfolio.header"))

    # Auth gate — shown as an inviting card rather than a plain warning
    if not st.session_state.get("token"):
        with st.container(border=True):
            st.markdown(f"### {t('portfolio.welcome_title')}")
            st.markdown(t("portfolio.welcome_body"))
            st.info(t("portfolio.welcome_hint"), icon=":material/lock:")
        return

    # Tabbed layout with icons in labels
    tab_portfolio, tab_watchlist, tab_chat = st.tabs(
        [t("portfolio.tab_portfolio"), t("portfolio.tab_watchlist"), t("portfolio.tab_chatbot")]
    )

    with tab_portfolio:
        _render_portfolio_section(_client)

    with tab_watchlist:
        _render_watchlist_section(_client)

    with tab_chat:
        render_chatbot(_client)


# ---------------------------------------------------------------------------
# Portfolio section
# ---------------------------------------------------------------------------


def _render_portfolio_section(client: APIClient) -> None:
    """Render the portfolio table, summary metrics, add form, and edit/delete controls."""
    positions = client.fetch_portfolio()

    if positions is None:
        st.error(t("portfolio.load_error"), icon=":material/block:")
        return

    # --- Portfolio summary and charts (Semaine 3) ---
    summary = client.fetch_portfolio_summary()
    if summary:
        with st.container(border=True):
            st.markdown(f"#### {t('portfolio.summary_header')}")
            col_val, col_pnl = st.columns(2)
            with col_val:
                total_val = summary.get("total_value", 0)
                st.metric(
                    t("portfolio.total_value"),
                    f"${float(total_val):,.2f}",
                )
            with col_pnl:
                pnl_pct = summary.get("pnl_pct", 0)
                st.metric(
                    t("portfolio.total_pnl"),
                    f"{float(pnl_pct):+.2f}%",
                )

        # Asset allocation pie chart
        allocation = summary.get("asset_allocation")
        if allocation:
            with st.container(border=True):
                st.markdown(f"#### {t('portfolio.allocation_title')}")
                render_portfolio_pie(allocation)

        # Portfolio history line chart
        history = client.fetch_portfolio_history()
        if history:
            with st.container(border=True):
                st.markdown(f"#### {t('portfolio.value_history_title')}")
                render_portfolio_history_chart(history)

    # --- Positions table or empty state ---
    with st.container(border=True):
        st.markdown(f"#### {t('portfolio.open_positions')}")
        if not positions:
            st.info(t("portfolio.empty"), icon=":material/inbox:")
        else:
            _render_portfolio_table(positions)

    # --- Edit / delete controls (only when positions exist) ---
    if positions:
        with st.container(border=True):
            st.markdown(f"#### {t('portfolio.edit_delete_header')}")
            _render_edit_delete(client, positions)

    # --- Add position form ---
    with st.container(border=True):
        st.markdown(f"#### ➕ {t('portfolio.add_header')}")
        _render_add_position_form(client)


def _render_portfolio_table(positions: list[dict[str, Any]]) -> None:
    """Display the portfolio positions as a styled dataframe with computed P&L columns."""
    rows: list[dict[str, Any]] = []
    for pos in positions:
        # Safe numeric conversion — guard against None values from the API
        entry_price = _safe_float(pos.get("entry_price"))
        current_price = _safe_float(pos.get("current_price") or pos.get("entry_price"))
        quantity = _safe_float(pos.get("quantity"))

        pnl_pct = (current_price - entry_price) / entry_price * 100 if entry_price else 0.0
        pnl_val = (current_price - entry_price) * quantity

        rows.append(
            {
                t("portfolio.col_crypto"): pos.get("symbol") or "?",
                t("portfolio.col_quantity"): quantity,
                t("portfolio.col_entry_price"): f"{entry_price:,.2f}",
                t("portfolio.col_current_price"): f"{current_price:,.2f}",
                t("portfolio.col_pnl_pct"): f"{pnl_pct:+.1f}%",
                t("portfolio.col_pnl_val"): f"{pnl_val:+,.2f}",
                t("portfolio.col_notes"): pos.get("notes") or "",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Portfolio summary metrics ---
    total_value = sum(
        _safe_float(p.get("current_price") or p.get("entry_price")) * _safe_float(p.get("quantity")) for p in positions
    )
    total_cost = sum(_safe_float(p.get("entry_price")) * _safe_float(p.get("quantity")) for p in positions)

    if total_cost > 0:
        total_pnl_pct = (total_value - total_cost) / total_cost * 100
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("portfolio.total_value"), f"${total_value:,.2f}")
        with col2:
            st.metric(t("portfolio.total_cost"), f"${total_cost:,.2f}")
        with col3:
            st.metric(
                t("portfolio.total_pnl"),
                f"{total_pnl_pct:+.1f}%",
                delta=f"${total_value - total_cost:+,.2f}",
            )


def _render_edit_delete(client: APIClient, positions: list[dict[str, Any]]) -> None:
    """Render inline edit and delete controls for an existing position."""
    # Build a human-readable label -> position mapping
    options: dict[str, dict[str, Any]] = {f"{p.get('symbol') or '?'}  (id {p.get('id', '?')})": p for p in positions}

    selected_label = st.selectbox(
        t("portfolio.select_position"),
        list(options.keys()),
        key="edit_select",
    )
    selected = options.get(selected_label or "")
    if not selected:
        return

    col_edit, col_delete = st.columns(2)

    # --- Edit form ---
    with col_edit, st.container(border=True):
        st.markdown(f"**{t('portfolio.edit_values')}**")
        with st.form("edit_position"):
            new_qty = st.number_input(
                t("portfolio.quantity"),
                value=_safe_float(selected.get("quantity")),
                min_value=0.0,
                step=0.001,
                key="edit_qty",
            )
            new_price = st.number_input(
                t("portfolio.entry_price"),
                value=_safe_float(selected.get("entry_price")),
                min_value=0.0,
                step=0.01,
                key="edit_price",
            )
            new_notes = st.text_input(
                t("portfolio.notes"),
                value=selected.get("notes") or "",
                key="edit_notes",
            )
            if st.form_submit_button(t("portfolio.save_changes"), use_container_width=True):
                if new_qty <= 0 or new_price <= 0:
                    st.warning("La quantite et le prix doivent etre superieurs a 0.", icon=":material/warning:")
                else:
                    result = client.update_portfolio_position(
                        selected["id"],
                        {
                            "quantity": new_qty,
                            "entry_price": new_price,
                            "notes": new_notes,
                        },
                    )
                    if result is not None:
                        st.success(t("portfolio.updated"))
                        st.rerun()
                    else:
                        st.error("Echec de la mise a jour. Verifiez la connexion API.")

    # --- Delete zone ---
    with col_delete, st.container(border=True):
        st.markdown(f"**{t('portfolio.delete_zone')}**")
        symbol_label = selected.get("symbol") or "?"
        st.warning(
            t("portfolio.delete_warning", symbol=symbol_label),
            icon=":material/warning:",
        )
        confirm = st.checkbox(t("portfolio.confirm_delete"), key="confirm_delete")
        if st.button(
            t("portfolio.delete_button"),
            type="primary",
            key="btn_delete",
            disabled=not confirm,
            use_container_width=True,
        ):
            result = client.delete_portfolio_position(selected["id"])
            if result is not None:
                st.success(t("portfolio.deleted", symbol=symbol_label))
                st.rerun()
            else:
                st.error("Echec de la suppression. Verifiez la connexion API.")


def _render_add_position_form(client: APIClient) -> None:
    """Render a form to add a new portfolio position."""
    with st.form("add_position"):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.selectbox(
                t("portfolio.col_crypto"),
                frontend_settings.tracked_symbols,
                key="add_symbol",
            )
        with col2:
            quantity = st.number_input(t("portfolio.quantity"), min_value=0.0, step=0.001, key="add_qty")
        with col3:
            entry_price = st.number_input(t("portfolio.entry_price"), min_value=0.0, step=0.01, key="add_price")

        notes = st.text_input(
            t("portfolio.notes_optional"), key="add_notes", placeholder=t("portfolio.notes_placeholder")
        )

        submitted = st.form_submit_button(t("portfolio.add_button"), use_container_width=True)

    # Validation and submission outside the form block
    if submitted:
        if not symbol:
            st.warning(t("portfolio.select_symbol_warning"), icon=":material/warning:")
        elif quantity <= 0:
            st.warning(t("portfolio.quantity_warning"), icon=":material/warning:")
        elif entry_price <= 0:
            st.warning(t("portfolio.price_warning"), icon=":material/warning:")
        else:
            result = client.add_portfolio_position(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "notes": notes.strip() or None,
                }
            )
            if result is not None:
                st.success(t("portfolio.added", symbol=symbol), icon=":material/check_circle:")
                st.rerun()


# ---------------------------------------------------------------------------
# Watchlist section
# ---------------------------------------------------------------------------


def _render_watchlist_section(client: APIClient) -> None:
    """Render the watchlist with add/remove controls."""
    watchlist = client.fetch_watchlist()

    if watchlist is None:
        st.error(t("watchlist.load_error"), icon=":material/block:")
        return

    # --- Current watchlist ---
    with st.container(border=True):
        st.markdown(f"#### {t('watchlist.header')}")

        if not watchlist:
            st.info(t("watchlist.empty"), icon=":material/inbox:")
        else:
            # Header row
            hdr_sym, hdr_action = st.columns([5, 1])
            hdr_sym.markdown(f"**{t('watchlist.col_symbol')}**")
            hdr_action.markdown(f"**{t('watchlist.col_action')}**")
            st.divider()

            for entry in watchlist:
                sym = entry.get("symbol") or "?"
                col_sym, col_rm = st.columns([5, 1])
                with col_sym:
                    st.markdown(f"**{sym}**")
                with col_rm:
                    if st.button(t("watchlist.remove"), key=f"rm_{sym}", use_container_width=True):
                        result = client.remove_from_watchlist(sym)
                        if result is not None:
                            st.success(t("watchlist.removed", symbol=sym))
                            st.rerun()

    # --- Add to watchlist ---
    with st.container(border=True):
        st.markdown(f"#### ➕ {t('watchlist.add_header')}")
        col_add, col_btn = st.columns([3, 1])
        with col_add:
            new_sym = st.selectbox(
                t("watchlist.add_label"),
                frontend_settings.tracked_symbols,
                key="wl_add_sym",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button(t("watchlist.add_button"), use_container_width=True, key="btn_wl_add", type="primary") and new_sym:
                result = client.add_to_watchlist(new_sym)
                if result is not None:
                    st.success(t("watchlist.added", symbol=new_sym), icon=":material/check_circle:")
                    st.rerun()


page()
