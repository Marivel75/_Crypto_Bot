"""
Tests unitaires pour le module de validation des données (DataValidator0HCLV : teste toutes les fonctionnalités de validation des données OHLCV.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.quality.validator import DataValidator0HCLV


class TestDataValidatorInitialization:
    """Tests pour l'initialisation du DataValidator0HCLV."""

    def test_initialization_with_default_values(self):
        """Test l'initialisation avec les valeurs par défaut."""
        validator = DataValidator0HCLV()

        assert validator.min_price == 0.01
        assert validator.max_volume == 1e12
        assert validator.allowed_exchanges == ["binance", "kraken", "coinbase"]


class TestDataframeStructureValidation:
    """Tests pour la validation de la structure du DataFrame."""

    def test_validate_empty_dataframe(self):
        """Test la validation d'un DataFrame vide."""
        validator = DataValidator0HCLV()
        empty_df = pd.DataFrame()

        is_valid, report = validator._validate_dataframe_structure(empty_df)

        assert not is_valid
        assert "DataFrame vide" in report["errors"]
        assert len(report["warnings"]) == 0

    def test_validate_missing_columns(self):
        """Test la validation avec des colonnes manquantes."""
        validator = DataValidator0HCLV()
        incomplete_df = pd.DataFrame(
            {
                "timestamp": [pd.Timestamp("2023-01-01")],
                "open": [100.0],
                "high": [101.0],
                # Colonnes manquantes dans le df pour ce test: low, close, volume, symbol, timeframe
            }
        )

        is_valid, report = validator._validate_dataframe_structure(incomplete_df)

        assert not is_valid
        assert "Colonnes manquantes" in report["errors"][0]
        assert "low" in report["errors"][0]
        assert "close" in report["errors"][0]

    def test_validate_valid_structure(self):
        """Test la validation d'une structure valide."""
        validator = DataValidator0HCLV()
        valid_df = pd.DataFrame(
            {
                "timestamp": [pd.Timestamp("2023-01-01")],
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [123.45],
                "symbol": ["BTC/USDT"],
                "timeframe": ["1h"],
            }
        )

        is_valid, report = validator._validate_dataframe_structure(valid_df)

        assert is_valid
        assert len(report["errors"]) == 0
        assert len(report["warnings"]) == 0


class TestPriceColumnValidation:
    """Tests pour la validation des colonnes de prix."""

    def test_validate_nan_price(self):
        """Test la validation d'un prix NaN."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_price_column(np.nan, "open")

        assert len(errors) == 1
        assert "open est NaN" in errors[0]
        assert len(warnings) == 0

    def test_validate_non_numeric_price(self):
        """Test la validation d'un prix non numérique."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_price_column("invalid", "high")

        assert len(errors) == 1
        assert "high n'est pas numérique" in errors[0]
        assert len(warnings) == 0

    def test_validate_negative_price(self):
        """Test la validation d'un prix négatif."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_price_column(-10.0, "low")

        assert len(errors) == 1
        assert "low doit être positif" in errors[0]
        assert len(warnings) == 0

    def test_validate_very_low_price(self):
        """Test la validation d'un prix très bas (warning)."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_price_column(0.001, "close")

        assert len(errors) == 0
        assert len(warnings) == 1
        assert "close très bas" in warnings[0]

    def test_validate_valid_price(self):
        """Test la validation d'un prix valide."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_price_column(100.5, "open")

        assert len(errors) == 0
        assert len(warnings) == 0


class TestVolumeValidation:
    """Tests pour la validation du volume."""

    def test_validate_nan_volume(self):
        """Test la validation d'un volume NaN."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_volume(np.nan)

        assert len(errors) == 1
        assert "volume est NaN" in errors[0]
        assert len(warnings) == 0

    def test_validate_negative_volume(self):
        """Test la validation d'un volume négatif."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_volume(-100.0)

        assert len(errors) == 1
        assert "volume ne peut pas être négatif" in errors[0]
        assert len(warnings) == 0

    def test_validate_very_high_volume(self):
        """Test la validation d'un volume très élevé (warning)."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_volume(1.1e12)

        assert len(errors) == 0
        assert len(warnings) == 1
        assert "volume très élevé" in warnings[0]

    def test_validate_valid_volume(self):
        """Test la validation d'un volume valide."""
        validator = DataValidator0HCLV()

        errors, warnings = validator._validate_volume(123.45)

        assert len(errors) == 0
        assert len(warnings) == 0


class TestPriceConsistencyValidation:
    """Tests pour la validation de la cohérence des prix."""

    def test_validate_high_less_than_low(self):
        """Test la validation quand high < low."""
        validator = DataValidator0HCLV()
        row = pd.Series(
            {
                "open": 100.0,
                "high": 95.0,  # Plus bas que low
                "low": 98.0,  # Plus haut que high
                "close": 101.0,
                "volume": 123.45,
            }
        )

        errors, warnings = validator._validate_price_consistency(row)

        assert len(errors) == 1
        assert "high (95.0) < low (98.0)" in errors[0]
        assert len(warnings) == 0

    def test_validate_negative_open_close(self):
        """Test la validation avec open ou close négatif."""
        validator = DataValidator0HCLV()
        row = pd.Series(
            {
                "open": -10.0,  # Négatif
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 123.45,
            }
        )

        errors, warnings = validator._validate_price_consistency(row)

        assert len(errors) == 1
        assert "prix d'ouverture ou de clôture négatif" in errors[0]
        assert len(warnings) == 0

    def test_validate_consistent_prices(self):
        """Test la validation de prix cohérents."""
        validator = DataValidator0HCLV()
        row = pd.Series(
            {
                "open": 100.0,
                "high": 102.0,
                "low": 98.0,
                "close": 101.0,
                "volume": 123.45,
            }
        )

        errors, warnings = validator._validate_price_consistency(row)

        assert len(errors) == 0
        assert len(warnings) == 0


class TestMetadataValidation:
    """Tests pour la validation des métadonnées."""

    def test_validate_invalid_symbol(self):
        """Test la validation d'un symbol invalide."""
        validator = DataValidator0HCLV()
        row = pd.Series({"symbol": "", "timeframe": "1h"})  # Vide

        errors, warnings = validator._validate_metadata(row)

        assert len(errors) == 1
        assert "symbol invalide" in errors[0]
        assert len(warnings) == 0

    def test_validate_invalid_timeframe(self):
        """Test la validation d'un timeframe invalide."""
        validator = DataValidator0HCLV()
        row = pd.Series({"symbol": "BTC/USDT", "timeframe": ""})  # Vide

        errors, warnings = validator._validate_metadata(row)

        assert len(errors) == 1
        assert "timeframe invalide" in errors[0]
        assert len(warnings) == 0

    def test_validate_valid_metadata(self):
        """Test la validation de métadonnées valides."""
        validator = DataValidator0HCLV()
        row = pd.Series({"symbol": "BTC/USDT", "timeframe": "1h"})

        errors, warnings = validator._validate_metadata(row)

        assert len(errors) == 0
        assert len(warnings) == 0


class TestCompleteOHLCVValidation:
    """Tests pour la validation complète des données OHLCV."""

    def test_validate_complete_valid_data(self):
        """Test la validation de données OHLCV complètement valides."""
        validator = DataValidator0HCLV()
        valid_data = pd.DataFrame(
            {
                "timestamp": [
                    pd.Timestamp("2023-01-01 10:00:00"),
                    pd.Timestamp("2023-01-01 11:00:00"),
                ],
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [98.0, 99.0],
                "close": [101.0, 102.0],
                "volume": [123.45, 234.56],
                "symbol": ["BTC/USDT", "BTC/USDT"],
                "timeframe": ["1h", "1h"],
            }
        )

        is_valid, report = validator.validate_ohlcv_values(valid_data)

        assert is_valid
        assert report["valid_rows"] == 2
        assert report["total_rows"] == 2
        assert report["validity_rate"] == 1.0
        assert len(report["errors"]) == 0
        assert len(report["warnings"]) == 0

    def test_validate_data_with_errors(self):
        """Test la validation de données avec des erreurs."""
        validator = DataValidator0HCLV()
        invalid_data = pd.DataFrame(
            {
                "timestamp": [pd.Timestamp("2023-01-01")],
                "open": [100.0],
                "high": [95.0],  # Plus bas que low
                "low": [98.0],  # Plus haut que high
                "close": [101.0],
                "volume": [123.45],
                "symbol": ["BTC/USDT"],
                "timeframe": ["1h"],
            }
        )

        is_valid, report = validator.validate_ohlcv_values(invalid_data)

        assert not is_valid
        assert report["valid_rows"] == 0
        assert report["total_rows"] == 1
        assert report["validity_rate"] == 0.0
        assert len(report["errors"]) == 1
        assert "high (95.0) < low (98.0)" in report["errors"][0]

    def test_validate_data_with_warnings(self):
        """Test la validation de données avec des warnings."""
        validator = DataValidator0HCLV()
        warning_data = pd.DataFrame(
            {
                "timestamp": [pd.Timestamp("2023-01-01")],
                "open": [0.005],  # Très bas
                "high": [0.01],
                "low": [0.004],
                "close": [0.006],
                "volume": [123.45],
                "symbol": ["BTC/USDT"],
                "timeframe": ["1h"],
            }
        )

        is_valid, report = validator.validate_ohlcv_values(warning_data)

        # Doit être valide (warnings ne bloquent pas la validation)
        assert is_valid
        assert report["valid_rows"] == 1
        assert len(report["warnings"]) >= 1
        assert any("très bas" in warning for warning in report["warnings"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
