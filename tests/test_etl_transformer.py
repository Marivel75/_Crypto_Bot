"""
Tests unitaires pour l'OHLCVTransformer.
Teste la transformation des données OHLCV.
"""

import pytest
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import datetime

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etl.transformer import OHLCVTransformer, TransformationError
from src.quality.validator import DataValidator0HCLV


class TestOHLCVTransformerInitialization:
    """Tests pour l'initialisation du transformeur."""

    def test_initialization_with_validator(self):
        """Test l'initialisation avec un valideur."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator, "binance")

        assert transformer.validator == mock_validator
        assert transformer.exchange == "binance"

    def test_initialization_with_custom_exchange(self):
        """Test l'initialisation avec un exchange personnalisé."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator, "kraken")

        assert transformer.exchange == "kraken"


class TestOHLCVTransformerTransform:
    """Tests pour la méthode transform."""

    def test_transform_success(self):
        """Test la transformation réussie."""
        # Configuration du mock valideur
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        mock_validator.validate_ohlcv_values.return_value = (True, {
            'valid_rows': 2,
            'total_rows': 2,
            'errors': [],
            'warnings': []
        })

        transformer = OHLCVTransformer(mock_validator)

        # Données brutes
        raw_data = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
            [1768298400000, 90050.0, 90150.0, 89950.0, 90100.0, 124.56],
        ]

        # Transformation
        result = transformer.transform(raw_data, "BTC/USDT", "1h")

        # Vérifications
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "symbol" in result.columns
        assert result["symbol"].iloc[0] == "BTC/USDT"
        assert result["timeframe"].iloc[0] == "1h"
        assert result["exchange"].iloc[0] == "binance"
        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])

        # Vérification des colonnes enrichies
        assert "price_range" in result.columns
        assert "price_change" in result.columns
        assert "price_change_pct" in result.columns

        # Vérification que le valideur a été appelé
        mock_validator.validate_ohlcv_values.assert_called_once()

    def test_transform_with_invalid_data(self):
        """Test la transformation avec des données invalides."""
        # Configuration du mock valideur pour retourner une erreur
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        mock_validator.validate_ohlcv_values.return_value = (False, {
            'valid_rows': 0,
            'total_rows': 1,
            'errors': ['Prix négatif détecté', 'Volume invalide'],
            'warnings': []
        })

        transformer = OHLCVTransformer(mock_validator)

        raw_data = [[1768294800000, -100.0, 90100.0, 89900.0, 90050.0, 123.45]]

        # Doit lever une exception
        with pytest.raises(TransformationError, match="Données invalides"):
            transformer.transform(raw_data, "BTC/USDT", "1h")

    def test_transform_with_empty_data(self):
        """Test la transformation avec des données vides."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator)

        # Doit lever une exception
        with pytest.raises(TransformationError, match="Aucune donnée à transformer"):
            transformer.transform([], "BTC/USDT", "1h")

    def test_transform_data_enrichment(self):
        """Test l'enrichissement des données."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        mock_validator.validate_ohlcv_values.return_value = (True, {
            'valid_rows': 1,
            'total_rows': 1,
            'errors': [],
            'warnings': []
        })

        transformer = OHLCVTransformer(mock_validator)

        # Donnée avec high=100, low=90, open=95, close=98
        raw_data = [[1768294800000, 95.0, 100.0, 90.0, 98.0, 1000.0]]

        result = transformer.transform(raw_data, "BTC/USDT", "1h")

        # Vérification des calculs
        assert result["price_range"].iloc[0] == 10.0  # 100 - 90
        assert result["price_change"].iloc[0] == 3.0   # 98 - 95
        assert abs(result["price_change_pct"].iloc[0] - 3.1578947) < 0.000001  # (3/95)*100


class TestOHLCVTransformerHelperMethods:
    """Tests pour les méthodes internes."""

    def test_to_dataframe(self):
        """Test la conversion en DataFrame."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator)

        raw_data = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
            [1768298400000, 90050.0, 90150.0, 89950.0, 90100.0, 124.56],
        ]

        df = transformer._to_dataframe(raw_data)

        assert len(df) == 2
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert df["open"].iloc[0] == 90000.0

    def test_add_metadata(self):
        """Test l'ajout des métadonnées."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator)

        df = pd.DataFrame({"timestamp": [1], "open": [2], "high": [3], "low": [4], "close": [5], "volume": [6]})
        result = transformer._add_metadata(df, "BTC/USDT", "1h")

        assert "symbol" in result.columns
        assert result["symbol"].iloc[0] == "BTC/USDT"
        assert result["timeframe"].iloc[0] == "1h"
        assert result["exchange"].iloc[0] == "binance"

    def test_convert_timestamps(self):
        """Test la conversion des timestamps."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator)

        # Utiliser un timestamp connu (1673600400000 = 2023-01-13 09:00:00 UTC)
        df = pd.DataFrame({"timestamp": [1673600400000]})
        result = transformer._convert_timestamps(df)

        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])
        # Vérifier que la colonne date existe et est de type date
        assert "date" in result.columns
        assert hasattr(result["date"].iloc[0], 'year')  # C'est un objet date

    def test_normalize_data(self):
        """Test la normalisation des données."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        transformer = OHLCVTransformer(mock_validator)

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2023-01-13", "2023-01-12"]),
            "open": ["90000", "91000"]  # Strings pour tester la conversion
        })

        result = transformer._normalize_data(df)

        # Doit être trié par timestamp
        assert result["timestamp"].iloc[0] < result["timestamp"].iloc[1]
        # Doit être numérique
        assert pd.api.types.is_numeric_dtype(result["open"])


class TestOHLCVTransformerBatch:
    """Tests pour la transformation en batch."""

    def test_transform_batch_success(self):
        """Test la transformation batch réussie."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)
        mock_validator.validate_ohlcv_values.return_value = (True, {
            'valid_rows': 1,
            'total_rows': 1,
            'errors': [],
            'warnings': []
        })

        transformer = OHLCVTransformer(mock_validator)

        batch_data = {
            "BTC/USDT": [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]],
            "ETH/USDT": [[1768294800000, 3000.0, 3010.0, 2990.0, 3005.0, 456.78]]
        }

        results = transformer.transform_batch(batch_data, "1h")

        assert len(results) == 2
        assert "BTC/USDT" in results
        assert "ETH/USDT" in results
        assert isinstance(results["BTC/USDT"], pd.DataFrame)
        assert isinstance(results["ETH/USDT"], pd.DataFrame)

    def test_transform_batch_partial_failure(self):
        """Test la transformation batch avec échec partiel."""
        mock_validator = MagicMock(spec=DataValidator0HCLV)

        # BTC réussit, ETH échoue
        def validate_side_effect(df):
            if df["symbol"].iloc[0] == "BTC/USDT":
                return (True, {'valid_rows': 1, 'total_rows': 1, 'errors': [], 'warnings': []})
            else:
                return (False, {'valid_rows': 0, 'total_rows': 1, 'errors': ['Données invalides'], 'warnings': []})

        mock_validator.validate_ohlcv_values.side_effect = validate_side_effect

        transformer = OHLCVTransformer(mock_validator)

        batch_data = {
            "BTC/USDT": [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]],
            "ETH/USDT": [[1768294800000, -3000.0, 3010.0, 2990.0, 3005.0, 456.78]]  # Prix négatif
        }

        results = transformer.transform_batch(batch_data, "1h")

        assert len(results) == 2
        assert results["BTC/USDT"] is not None
        assert results["ETH/USDT"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
