"""Internationalisation helpers for the Crypto Bot frontend.

Usage::

    from src.frontend.i18n import t

    st.header(t("dashboard.header"))
    st.info(t("dashboard.no_ohlcv_data", symbol="BTC", timeframe="4h"))
"""

from __future__ import annotations

import logging

import streamlit as st

from src.frontend.i18n.en import TRANSLATIONS as EN
from src.frontend.i18n.fr import TRANSLATIONS as FR

logger = logging.getLogger(__name__)

_CATALOGS: dict[str, dict[str, str]] = {
    "fr": FR,
    "en": EN,
}


def get_lang() -> str:
    """Return the active language code from session state (default ``"fr"``)."""
    return str(st.session_state.get("lang", "fr"))


def set_lang(lang: str) -> None:
    """Set the active language in session state."""
    st.session_state["lang"] = lang


def t(key: str, **kwargs: object) -> str:
    """Translate *key* into the active language.

    Fallback chain: active language -> French -> raw key.
    Supports ``str.format`` interpolation via **kwargs**.

    Args:
        key: Dot-notation translation key (e.g. ``"dashboard.header"``).
        **kwargs: Values for ``str.format`` placeholders in the translated string.

    Returns:
        Translated (and optionally formatted) string.
    """
    lang = get_lang()
    catalog = _CATALOGS.get(lang, FR)

    text = catalog.get(key) or FR.get(key) or key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            logger.warning("Missing format key in translation %r (%s): %s", key, lang, kwargs)

    return text
