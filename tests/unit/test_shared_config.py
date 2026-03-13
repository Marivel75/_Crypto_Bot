"""Unit tests for the shared Settings configuration class."""

from __future__ import annotations

import pytest

from src.shared.config import Settings, settings

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    def test_database_url_has_default(self) -> None:
        s = Settings()
        assert s.database_url.startswith("postgresql://")

    def test_postgres_db_default(self) -> None:
        s = Settings()
        assert s.postgres_db == "cryptobot"

    def test_postgres_user_default(self) -> None:
        s = Settings()
        assert s.postgres_user == "cryptobot"

    def test_minio_endpoint_default(self) -> None:
        s = Settings()
        assert "minio" in s.minio_endpoint

    def test_minio_root_user_default(self) -> None:
        s = Settings()
        assert s.minio_root_user == "minioadmin"

    def test_api_host_default(self) -> None:
        s = Settings()
        assert s.api_host == "0.0.0.0"  # noqa: S104

    def test_api_port_default(self) -> None:
        s = Settings()
        assert s.api_port == 8000

    def test_api_url_default(self) -> None:
        s = Settings()
        assert "api" in s.api_url

    def test_coingecko_api_key_empty_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Test optional API key defaults to empty when env var is not set
        monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
        # Set all required env vars to allow Settings instantiation
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test")
        monkeypatch.setenv("MINIO_ROOT_USER", "test")
        monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test")
        monkeypatch.setenv("API_SECRET_KEY", "test")
        monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "test")
        from pydantic_settings import SettingsConfigDict

        class TestSettings(Settings):
            model_config = SettingsConfigDict(env_file=None, extra="ignore")

        s = TestSettings()
        assert s.coingecko_api_key == ""

    def test_openai_api_key_empty_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Test optional API key defaults to empty when env var is not set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Set all required env vars to allow Settings instantiation
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test")
        monkeypatch.setenv("MINIO_ROOT_USER", "test")
        monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test")
        monkeypatch.setenv("API_SECRET_KEY", "test")
        monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "test")
        from pydantic_settings import SettingsConfigDict

        class TestSettings(Settings):
            model_config = SettingsConfigDict(env_file=None, extra="ignore")

        s = TestSettings()
        assert s.openai_api_key == ""

    def test_anthropic_api_key_empty_by_default(self) -> None:
        s = Settings()
        assert s.anthropic_api_key == ""

    def test_mlflow_tracking_uri_default(self) -> None:
        s = Settings()
        assert "mlflow" in s.mlflow_tracking_uri

    def test_log_level_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        s = Settings()
        assert s.log_level == "INFO"

    def test_jwt_expiration_hours_default(self) -> None:
        s = Settings()
        assert s.jwt_expiration_hours == 24

    def test_tracked_symbols_is_list(self) -> None:
        s = Settings()
        assert isinstance(s.tracked_symbols, list)
        assert len(s.tracked_symbols) > 0

    def test_tracked_symbols_contains_priority_cryptos(self) -> None:
        s = Settings()
        priority = {"BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "SOL"}
        assert priority.issubset(set(s.tracked_symbols))

    def test_timeframes_is_list(self) -> None:
        s = Settings()
        assert isinstance(s.timeframes, list)
        assert "1h" in s.timeframes
        assert "4h" in s.timeframes
        assert "1D" in s.timeframes

    def test_cors_origins_is_list(self) -> None:
        s = Settings()
        assert isinstance(s.cors_origins, list)
        assert len(s.cors_origins) > 0


# ---------------------------------------------------------------------------
# Env var overrides via monkeypatch
# ---------------------------------------------------------------------------


class TestSettingsEnvOverrides:
    def test_api_port_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API_PORT", "9090")
        s = Settings()
        assert s.api_port == 9090

    def test_log_level_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == "DEBUG"

    def test_database_url_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        custom_url = "postgresql://user:pass@localhost:5432/mydb"
        monkeypatch.setenv("DATABASE_URL", custom_url)
        s = Settings()
        assert s.database_url == custom_url

    def test_coingecko_api_key_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COINGECKO_API_KEY", "cg-test-key-abc123")
        s = Settings()
        assert s.coingecko_api_key == "cg-test-key-abc123"

    def test_jwt_expiration_hours_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_EXPIRATION_HOURS", "48")
        s = Settings()
        assert s.jwt_expiration_hours == 48

    def test_minio_endpoint_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MINIO_ENDPOINT", "http://storage.internal:9000")
        s = Settings()
        assert s.minio_endpoint == "http://storage.internal:9000"

    def test_api_secret_key_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API_SECRET_KEY", "super-secret-key-for-tests")
        s = Settings()
        assert s.api_secret_key == "super-secret-key-for-tests"  # noqa: S105

    def test_mlflow_tracking_uri_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        s = Settings()
        assert s.mlflow_tracking_uri == "http://localhost:5000"


# ---------------------------------------------------------------------------
# Settings singleton
# ---------------------------------------------------------------------------


class TestSettingsSingleton:
    def test_singleton_is_settings_instance(self) -> None:
        assert isinstance(settings, Settings)

    def test_singleton_is_module_level(self) -> None:
        # Re-importing should give the same object
        from src.shared.config import settings as settings2

        assert settings is settings2

    def test_singleton_has_expected_fields(self) -> None:
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "api_port")
        assert hasattr(settings, "log_level")
        assert hasattr(settings, "tracked_symbols")
        assert hasattr(settings, "timeframes")

    def test_singleton_tracked_symbols_nonempty(self) -> None:
        assert len(settings.tracked_symbols) > 0

    def test_singleton_timeframes_includes_standard(self) -> None:
        standard = {"1h", "4h", "1D"}
        assert standard.issubset(set(settings.timeframes))
