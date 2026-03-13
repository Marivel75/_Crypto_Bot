"""Crypto Bot — Streamlit entry point.

Configures page, injects the professional adaptive theme (light + dark),
sets up Lucide icon helpers, renders sidebar auth, and wires navigation.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work when Streamlit
# launches this file directly.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.config import frontend_settings
from src.frontend.i18n import t

logging.basicConfig(
    level=getattr(logging, frontend_settings.log_level, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config — MUST be the first Streamlit call in the script.
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Crypto Bot",
    page_icon=":material/candlestick_chart:",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------------------------
# Lucide Icons CDN — loaded once via a hidden HTML component.
# Using lucide-static so individual <i> tags work without JS bundling.
# ---------------------------------------------------------------------------
_LUCIDE_CDN = "https://cdn.jsdelivr.net/npm/lucide-static@latest/font/lucide.min.css"

st.markdown(
    f'<link rel="stylesheet" href="{_LUCIDE_CDN}">',
    unsafe_allow_html=True,
)


def lucide_icon(name: str, size: int = 20, color: str | None = None) -> str:
    """Return an HTML string for a Lucide icon usable with st.markdown.

    Args:
        name:  Lucide icon slug, e.g. ``"trending-up"``, ``"bell"``.
        size:  Font size in pixels (controls icon dimensions). Defaults to 20.
        color: CSS color string. When ``None`` the icon inherits ``currentColor``.

    Returns:
        An ``<i>`` tag string. Pass to ``st.markdown(..., unsafe_allow_html=True)``.

    Example::

        st.markdown(lucide_icon("trending-up", size=24, color="#22d3ee"),
                    unsafe_allow_html=True)
    """
    color_style = f"color:{color};" if color else ""
    return f'<i class="icon-{name}" style="font-size:{size}px;vertical-align:middle;{color_style}"></i>'


# ---------------------------------------------------------------------------
# Adaptive theme CSS — works in both Streamlit light and dark modes.
# Uses [data-theme] selectors that Streamlit sets on <html> / <body>,
# with CSS custom properties so all rules reference a single palette.
# ---------------------------------------------------------------------------
_THEME_CSS = """
<style>
/* ============================================================
   CSS CUSTOM PROPERTIES — dark palette (Streamlit dark mode)
   ============================================================ */
[data-theme="dark"],
html[data-theme="dark"] body {
    --cb-bg:          #0d1117;
    --cb-surface:     #161b22;
    --cb-surface-2:   #1c2433;
    --cb-border:      #30363d;
    --cb-accent:      #22d3ee;        /* cyan-400  */
    --cb-accent-2:    #0ea5e9;        /* sky-500   */
    --cb-accent-dim:  rgba(34,211,238,.12);
    --cb-text:        #e6edf3;
    --cb-text-muted:  #8b949e;
    --cb-success:     #3fb950;
    --cb-warning:     #d29922;
    --cb-error:       #f85149;
    --cb-shadow:      0 4px 20px rgba(0,0,0,.55);
    --cb-shadow-sm:   0 2px 8px  rgba(0,0,0,.40);
}

/* ============================================================
   CSS CUSTOM PROPERTIES — light palette (Streamlit light mode)
   ============================================================ */
[data-theme="light"],
html[data-theme="light"] body {
    --cb-bg:          #f6f8fa;
    --cb-surface:     #ffffff;
    --cb-surface-2:   #eef2f7;
    --cb-border:      #d0d7de;
    --cb-accent:      #0284c7;        /* sky-600   */
    --cb-accent-2:    #0369a1;        /* sky-700   */
    --cb-accent-dim:  rgba(2,132,199,.10);
    --cb-text:        #1f2328;
    --cb-text-muted:  #57606a;
    --cb-success:     #1a7f37;
    --cb-warning:     #9a6700;
    --cb-error:       #cf222e;
    --cb-shadow:      0 4px 20px rgba(0,0,0,.10);
    --cb-shadow-sm:   0 2px 8px  rgba(0,0,0,.07);
}

/* ============================================================
   SYSTEM-LEVEL FALLBACK (no Streamlit data-theme attribute yet)
   ============================================================ */
@media (prefers-color-scheme: dark) {
    :root {
        --cb-bg:         #0d1117;
        --cb-surface:    #161b22;
        --cb-surface-2:  #1c2433;
        --cb-border:     #30363d;
        --cb-accent:     #22d3ee;
        --cb-accent-2:   #0ea5e9;
        --cb-accent-dim: rgba(34,211,238,.12);
        --cb-text:       #e6edf3;
        --cb-text-muted: #8b949e;
        --cb-success:    #3fb950;
        --cb-warning:    #d29922;
        --cb-error:      #f85149;
        --cb-shadow:     0 4px 20px rgba(0,0,0,.55);
        --cb-shadow-sm:  0 2px 8px  rgba(0,0,0,.40);
    }
}
@media (prefers-color-scheme: light) {
    :root {
        --cb-bg:         #f6f8fa;
        --cb-surface:    #ffffff;
        --cb-surface-2:  #eef2f7;
        --cb-border:     #d0d7de;
        --cb-accent:     #0284c7;
        --cb-accent-2:   #0369a1;
        --cb-accent-dim: rgba(2,132,199,.10);
        --cb-text:       #1f2328;
        --cb-text-muted: #57606a;
        --cb-success:    #1a7f37;
        --cb-warning:    #9a6700;
        --cb-error:      #cf222e;
        --cb-shadow:     0 4px 20px rgba(0,0,0,.10);
        --cb-shadow-sm:  0 2px 8px  rgba(0,0,0,.07);
    }
}

/* ============================================================
   GRADIENT ACCENT BAR — top of the viewport
   ============================================================ */
.stApp::before {
    content: "";
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(
        90deg,
        var(--cb-accent-2) 0%,
        var(--cb-accent)   50%,
        var(--cb-accent-2) 100%
    );
    z-index: 9999;
}

/* ============================================================
   MAIN APP BACKGROUND & TEXT
   ============================================================ */
.stApp {
    background-color: var(--cb-bg);
    color: var(--cb-text);
}

/* ============================================================
   SIDEBAR
   ============================================================ */
[data-testid="stSidebar"] {
    background-color: var(--cb-surface);
    border-right: 1px solid var(--cb-border);
    padding-top: 1rem;
}

/* Sidebar brand title */
[data-testid="stSidebar"] h1 {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, var(--cb-accent), var(--cb-accent-2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.25rem;
}

/* Sidebar nav links */
[data-testid="stSidebarNavItems"] a {
    border-radius: 8px;
    margin: 2px 0;
    padding: 6px 12px;
    transition: background 0.15s ease;
}
[data-testid="stSidebarNavItems"] a:hover {
    background-color: var(--cb-accent-dim);
}
[data-testid="stSidebarNavItems"] a[aria-selected="true"] {
    background-color: var(--cb-accent-dim);
    color: var(--cb-accent);
    font-weight: 600;
}

/* Sidebar caption / footer */
[data-testid="stSidebar"] .stCaption {
    color: var(--cb-text-muted);
    font-size: 0.75rem;
    text-align: center;
    padding: 0 0.5rem;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: var(--cb-border);
    margin: 0.75rem 0;
}

/* ============================================================
   METRIC CARDS
   ============================================================ */
[data-testid="stMetric"] {
    background-color: var(--cb-surface);
    border: 1px solid var(--cb-border);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: var(--cb-shadow-sm);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--cb-shadow);
    transform: translateY(-1px);
}
[data-testid="stMetricLabel"] {
    color: var(--cb-text-muted);
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--cb-text);
}
[data-testid="stMetricDelta"] {
    font-size: 0.82rem;
    font-weight: 500;
}

/* ============================================================
   CONTAINERS / CARDS
   ============================================================ */
div[data-testid="stContainer"] {
    border-radius: 12px;
    border: 1px solid var(--cb-border);
    box-shadow: var(--cb-shadow-sm);
    background-color: var(--cb-surface);
}

/* ============================================================
   ALERT BOXES (info / warning / error / success)
   ============================================================ */
.stAlert {
    border-radius: 10px;
    border-width: 1px;
    border-style: solid;
    box-shadow: var(--cb-shadow-sm);
}
/* Info */
[data-baseweb="notification"][kind="info"],
div[data-testid="stInfo"] {
    background-color: var(--cb-accent-dim);
    border-color: var(--cb-accent);
    color: var(--cb-text);
}
/* Warning */
div[data-testid="stWarning"] {
    border-color: var(--cb-warning);
}
/* Error */
div[data-testid="stError"] {
    border-color: var(--cb-error);
}
/* Success */
div[data-testid="stSuccess"] {
    border-color: var(--cb-success);
}

/* ============================================================
   BUTTONS
   ============================================================ */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.15s ease;
    border: 1px solid var(--cb-accent);
    color: var(--cb-accent);
    background: transparent;
}
.stButton > button:hover {
    background: var(--cb-accent-dim);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(34,211,238,.25);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--cb-accent-2), var(--cb-accent));
    color: #fff;
    border: none;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.9;
    box-shadow: 0 4px 16px rgba(34,211,238,.40);
}

/* ============================================================
   TABS
   ============================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--cb-border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    padding: 6px 16px;
    font-weight: 500;
    color: var(--cb-text-muted);
    background: transparent;
    transition: background 0.15s;
}
.stTabs [aria-selected="true"] {
    color: var(--cb-accent);
    border-bottom: 2px solid var(--cb-accent);
    background: var(--cb-accent-dim);
}

/* ============================================================
   INPUT FIELDS
   ============================================================ */
.stTextInput input,
.stSelectbox select,
.stTextArea textarea {
    border-radius: 8px;
    border: 1px solid var(--cb-border);
    background-color: var(--cb-surface-2);
    color: var(--cb-text);
    transition: border-color 0.15s;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--cb-accent);
    box-shadow: 0 0 0 3px var(--cb-accent-dim);
}

/* ============================================================
   DATAFRAMES / TABLES
   ============================================================ */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--cb-border);
    box-shadow: var(--cb-shadow-sm);
}

/* ============================================================
   SCROLLBAR — subtle, theme-aware
   ============================================================ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--cb-surface); }
::-webkit-scrollbar-thumb {
    background: var(--cb-border);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--cb-text-muted); }

/* ============================================================
   RESPONSIVE — prevent horizontal overflow globally
   ============================================================ */
.main .block-container {
    max-width: 100% !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* ============================================================
   RESPONSIVE — MOBILE (max-width: 768px)
   ============================================================ */
@media (max-width: 768px) {
    /* Stack columns vertically */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* Sidebar: allow collapse to zero width */
    [data-testid="stSidebar"] {
        min-width: 0 !important;
    }

    /* Metrics: tighter padding on small screens */
    [data-testid="stMetric"] {
        padding: 8px 12px !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }

    /* Tables: horizontal scroll */
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
    }

    /* Touch-friendly buttons and inputs */
    .stButton > button {
        min-height: 44px !important;
    }
    .stTextInput input,
    .stSelectbox select,
    .stTextArea textarea {
        min-height: 44px !important;
    }

    /* Smaller headings on mobile */
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.1rem !important; }

    /* Plotly charts: prevent overflow */
    .js-plotly-plot, .plotly {
        max-width: 100% !important;
        overflow: hidden !important;
    }
}

/* ============================================================
   RESPONSIVE — TABLET (769px – 1024px)
   ============================================================ */
@media (max-width: 1024px) and (min-width: 769px) {
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
    [data-testid="stMetric"] {
        padding: 12px 16px !important;
    }
}
</style>
"""

st.markdown(_THEME_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    """Initialize session state defaults on first load."""
    defaults: dict[str, object] = {
        "token": None,
        "username": None,
        "email": None,
        "chat_history": [],
        "sidebar_tab": "login",
        "lang": "fr",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # Lazy-init APIClient to avoid eager construction on every rerun.
    if "api_client" not in st.session_state:
        st.session_state["api_client"] = APIClient()


# ---------------------------------------------------------------------------
# Sidebar rendering
# ---------------------------------------------------------------------------


def _render_sidebar_auth() -> None:
    """Render login/register controls in the sidebar."""
    with st.sidebar:
        # Brand header with gradient icon
        st.markdown(
            f"{lucide_icon('trending-up', size=22, color='var(--cb-accent)')} "
            "<span style='font-size:1.2rem;font-weight:700;letter-spacing:-0.02em;'>"
            "Crypto Bot</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='color:var(--cb-text-muted);font-size:0.75rem;"
            f"margin-top:-6px;margin-bottom:12px;'>{t('app.subtitle')}</p>",
            unsafe_allow_html=True,
        )

        st.divider()

        # Language selector
        _lang_options = {"Francais": "fr", "English": "en"}
        _lang_labels = list(_lang_options.keys())
        _current_idx = _lang_labels.index(
            next(k for k, v in _lang_options.items() if v == st.session_state.get("lang", "fr"))
        )
        _selected_lang_label = st.selectbox(
            t("app.language"),
            _lang_labels,
            index=_current_idx,
            key="lang_selector",
        )
        _new_lang = _lang_options[_selected_lang_label]
        if _new_lang != st.session_state.get("lang"):
            st.session_state["lang"] = _new_lang
            st.rerun()

        st.divider()

        if st.session_state.get("token"):
            # Logged-in state: show user badge and logout button.
            username = st.session_state.get("username", "?")
            st.markdown(
                f"{lucide_icon('circle-user', size=16, color='var(--cb-success)')} "
                f"<span style='color:var(--cb-success);font-weight:600;"
                f"font-size:0.85rem;'>{username}</span>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(t("auth.logout"), use_container_width=True):
                st.session_state["token"] = None
                st.session_state["username"] = None
                st.session_state["email"] = None
                st.session_state["chat_history"] = []
                logger.info("User logged out")
                st.rerun()
        else:
            # Auth tabs: Login / Register.
            tab_login, tab_register = st.tabs([t("auth.tab_login"), t("auth.tab_register")])

            with tab_login:
                _render_login_form()

            with tab_register:
                _render_register_form()

        st.divider()
        st.caption(t("app.disclaimer"))


def _render_login_form() -> None:
    """Render the login form inside the sidebar."""
    email = st.text_input(t("auth.email"), key="login_email", placeholder="user@example.com")
    password = st.text_input(t("auth.password"), type="password", key="login_pass")

    if st.button(t("auth.login_button"), use_container_width=True, key="btn_login"):
        if not email or not password:
            st.warning(t("auth.fill_all_fields"))
            return

        client: APIClient = st.session_state["api_client"]
        token = client.login(email.strip(), password)
        if token:
            st.session_state["token"] = token
            # Fetch actual username from /auth/me.
            me = client.get_me()
            st.session_state["username"] = me.get("username", email) if me else email
            st.session_state["email"] = email
            logger.info("User logged in: %s", email)
            st.rerun()
        else:
            st.error(t("auth.invalid_credentials"))


def _render_register_form() -> None:
    """Render the registration form inside the sidebar."""
    username = st.text_input(t("auth.username"), key="reg_username")
    email = st.text_input(t("auth.email"), key="reg_email", placeholder="user@example.com")
    password = st.text_input(t("auth.password"), type="password", key="reg_pass")
    persona = st.selectbox(
        t("auth.profile"),
        ["trader", "journalist", "investor"],
        key="reg_persona",
    )

    if st.button(t("auth.register_button"), use_container_width=True, key="btn_register"):
        if not username or not email or not password:
            st.warning(t("auth.fill_all_fields"))
            return

        client: APIClient = st.session_state["api_client"]
        result = client.register(
            username=username.strip(),
            email=email.strip(),
            password=password,
            persona_type=persona,
        )
        if result is not None:
            logger.info("New user registered: %s", email)
            token = client.login(email.strip(), password)
            if token:
                st.session_state["token"] = token
                me = client.get_me()
                st.session_state["username"] = me.get("username", email) if me else username.strip()
                st.session_state["email"] = email.strip()
                st.rerun()
            else:
                st.success(t("auth.account_created"))
        else:
            st.error(t("auth.register_failed"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_init_session_state()
_render_sidebar_auth()

# --- Navigation ---
_PAGES_DIR = Path(__file__).resolve().parent / "pages"
dashboard = st.Page(str(_PAGES_DIR / "1_dashboard.py"), title=t("nav.dashboard"), icon=":material/trending_up:")
veille = st.Page(str(_PAGES_DIR / "2_veille.py"), title=t("nav.veille"), icon=":material/newspaper:")
portfolio = st.Page(
    str(_PAGES_DIR / "3_portfolio.py"), title=t("nav.portfolio"), icon=":material/account_balance_wallet:"
)
analytics = st.Page(str(_PAGES_DIR / "4_analytics.py"), title=t("nav.analytics"), icon=":material/analytics:")
performance = st.Page(str(_PAGES_DIR / "5_performance.py"), title=t("nav.performance"), icon=":material/emoji_events:")

nav = st.navigation([dashboard, veille, portfolio, analytics, performance])
nav.run()
