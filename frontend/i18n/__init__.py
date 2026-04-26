"""i18n helper — French only for now."""

from __future__ import annotations

from frontend.i18n.fr import TRANSLATIONS


def t(key: str, **kwargs: object) -> str:
    """Return the French translation for *key*, formatted with **kwargs.

    Falls back to the key itself when no translation is found.
    """
    template = TRANSLATIONS.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template
