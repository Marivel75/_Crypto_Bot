"""Test factories for SQLAlchemy ORM models.

Provides helper functions returning UserOrm instances suitable for
unit and integration tests. Passwords are hashed with bcrypt.
UUIDs are generated with uuid4 so each call produces a unique user.

The alias ``UserOrmFactory`` is provided for import compatibility with
the package ``__init__.py``.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

UTC = timezone.utc

import bcrypt as _bcrypt

from src.shared.db_models import UserOrm

# Fixed creation timestamp — never datetime.now() in tests
_FIXED_TS = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)

# Plain-text value used only for test hashing — not a real secret.
_TEST_PLAIN_PW = "test-only-not-a-secret"  # noqa: S105


def make_user(**overrides: object) -> UserOrm:
    """Return an unsaved UserOrm instance with realistic defaults.

    A new uuid4 is generated for ``id`` on every call unless overridden,
    so multiple calls produce distinct users without collisions.

    The value of ``_TEST_PLAIN_PW`` is hashed with bcrypt before being
    stored in ``password_hash``. Pass ``password_hash`` directly in
    ``overrides`` to skip hashing.

    Args:
        **overrides: Any UserOrm attribute to override.

    Returns:
        An unsaved UserOrm instance (not bound to a database session).

    Example::

        user = make_user(username="alice", email="alice@example.com")
        investor = make_user(persona_type="investor")
    """
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "username": "testuser",
        "email": "testuser@example.com",
        "password_hash": _bcrypt.hashpw(_TEST_PLAIN_PW.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8"),
        "persona_type": "trader",
        "preferences": {},
        "created_at": _FIXED_TS,
    }
    defaults.update(overrides)

    user = UserOrm()
    for key, value in defaults.items():
        setattr(user, key, value)
    return user


def make_journalist_user(**overrides: object) -> UserOrm:
    """Return a UserOrm pre-configured with the journalist persona.

    Args:
        **overrides: Any UserOrm attribute to override.

    Returns:
        An unsaved UserOrm instance.
    """
    journalist_defaults: dict[str, object] = {
        "username": "journalist_user",
        "email": "journalist@example.com",
        "persona_type": "journalist",
    }
    journalist_defaults.update(overrides)
    return make_user(**journalist_defaults)


def make_investor_user(**overrides: object) -> UserOrm:
    """Return a UserOrm pre-configured with the investor persona.

    Args:
        **overrides: Any UserOrm attribute to override.

    Returns:
        An unsaved UserOrm instance.
    """
    investor_defaults: dict[str, object] = {
        "username": "investor_user",
        "email": "investor@example.com",
        "persona_type": "investor",
    }
    investor_defaults.update(overrides)
    return make_user(**investor_defaults)


# ---------------------------------------------------------------------------
# Alias for import compatibility (tests/factories/__init__.py)
# ---------------------------------------------------------------------------

#: Callable alias for make_user — use ``make_user`` directly in tests.
UserOrmFactory: Callable[..., UserOrm] = make_user
