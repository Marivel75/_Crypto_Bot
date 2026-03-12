"""Tests for frontend configuration."""

from __future__ import annotations

from src.frontend.config import FrontendSettings, frontend_settings


class TestFrontendSettings:
    """Verify default values and frozen behavior."""

    def test_default_api_url(self) -> None:
        settings = FrontendSettings()
        assert settings.api_url == "http://api:8000"

    def test_default_timeouts(self) -> None:
        settings = FrontendSettings()
        assert settings.api_timeout == 10.0
        assert settings.api_connect_timeout == 5.0

    def test_default_cache_ttls(self) -> None:
        settings = FrontendSettings()
        assert settings.cache_ttl_prices == 30
        assert settings.cache_ttl_signals == 60
        assert settings.cache_ttl_news == 300
        assert settings.cache_ttl_market == 300

    def test_default_tracked_symbols(self) -> None:
        settings = FrontendSettings()
        assert "BTC" in settings.tracked_symbols
        assert "ETH" in settings.tracked_symbols
        assert len(settings.tracked_symbols) == 11

    def test_stablecoins_excluded(self) -> None:
        settings = FrontendSettings()
        assert "USDT" not in settings.tracked_symbols
        assert "USDC" not in settings.tracked_symbols

    def test_default_timeframes(self) -> None:
        settings = FrontendSettings()
        assert settings.timeframes == ["1h", "2h", "3h", "4h", "1D", "1W", "1M"]

    def test_log_level_is_valid(self) -> None:
        settings = FrontendSettings()
        assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def test_frozen_model(self) -> None:
        settings = FrontendSettings()
        try:
            settings.api_url = "http://other:9000"  # type: ignore[misc]
            raised = False
        except Exception:
            raised = True
        assert raised, "FrontendSettings should be frozen (immutable)"

    def test_singleton_instance_exists(self) -> None:
        assert frontend_settings is not None
        assert isinstance(frontend_settings, FrontendSettings)
