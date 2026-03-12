"""Unit tests for shared config."""

from __future__ import annotations

from src.shared.config import settings


class TestSettings:
    def test_default_values(self) -> None:
        assert settings.api_port == 8000
        assert settings.log_level in ("INFO", "DEBUG", "WARNING")
        assert settings.jwt_expiration_hours == 24
        assert len(settings.tracked_symbols) > 0

    def test_tracked_symbols_contains_btc(self) -> None:
        assert "BTC" in settings.tracked_symbols

    def test_timeframes_not_empty(self) -> None:
        assert len(settings.timeframes) > 0

    def test_cors_origins(self) -> None:
        assert isinstance(settings.cors_origins, list)
