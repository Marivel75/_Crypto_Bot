"""Crypto Bot — Streamlit entry point.

Lance avec : streamlit run frontend/app.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from frontend.config import frontend_settings
from frontend.i18n import t

logging.basicConfig(
    level=getattr(logging, frontend_settings.log_level, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# MUST be the first Streamlit call
st.set_page_config(
    page_title="Crypto Bot",
    page_icon=":material/candlestick_chart:",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------------------------
# Adaptive dark theme CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
[data-theme="dark"], html[data-theme="dark"] body {
    --cb-bg: #0d1117; --cb-surface: #161b22; --cb-border: #30363d;
    --cb-accent: #22d3ee; --cb-text: #e6edf3; --cb-text-muted: #8b949e;
}
[data-theme="light"], html[data-theme="light"] body {
    --cb-bg: #ffffff; --cb-surface: #f6f8fa; --cb-border: #d0d7de;
    --cb-accent: #0ea5e9; --cb-text: #1f2328; --cb-text-muted: #636c76;
}
[data-testid="stSidebar"] { background-color: var(--cb-surface); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Multi-page navigation
# ---------------------------------------------------------------------------
pg = st.navigation([
    st.Page("pages/1_dashboard.py", title=t("nav.dashboard"), icon=":material/candlestick_chart:"),
    st.Page("pages/2_analytics.py", title=t("nav.analytics"), icon=":material/analytics:"),
    st.Page("pages/3_signals.py", title=t("nav.signals"), icon=":material/signal_cellular_alt:"),
])

# Sidebar branding
with st.sidebar:
    st.markdown(f"### Crypto Bot")
    st.caption(t("app.subtitle"))
    st.divider()
    st.caption(t("app.disclaimer"))

pg.run()
