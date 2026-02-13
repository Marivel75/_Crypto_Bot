"""
Tests unitaires pour l'OHLCVExtractor.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etl.ohlcv_pipeline.extractor import OHLCVExtractor, ExtractionError


class TestOHLCVExtractorInitialization:
    """Tests pour l'initialisation de l'extracteur."""

    def test_initialization_with_client(self):
        """Test l'initialisation avec un client mock."""
        mock_client = MagicMock()
        mock_client.__class__.__name__ = "MockClient"

        extractor = OHLCVExtractor(mock_client)

        assert extractor.client == mock_client
        assert extractor.max_retries == 3

    def test_initialization_with_custom_retries(self):
        """Test l'initialisation avec un nombre personnalisé de tentatives."""
        mock_client = MagicMock()
        extractor = OHLCVExtractor(mock_client, max_retries=5)

        assert extractor.max_retries == 5


class TestOHLCVExtractorExtract:
    """Tests pour la méthode extract."""

    def test_extract_success(self):
        """Test l'extraction réussie."""
        # Configuration du mock
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
            [1768298400000, 90050.0, 90150.0, 89950.0, 90100.0, 124.56],
        ]

        extractor = OHLCVExtractor(mock_client)

        # Exécution
        result = extractor.extract("BTC/USDT", "1h", 100)

        # Vérifications
        assert len(result) == 2
        assert result[0][0] == 1768294800000  # timestamp
        assert result[0][5] == 123.45  # volume
        mock_client.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1h", 100)

    def test_extract_empty_data(self):
        """Test l'extraction quand aucune donnée n'est retournée."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = []

        extractor = OHLCVExtractor(mock_client)

        # Doit lever une exception
        with pytest.raises(ExtractionError, match="Aucune donnée retournée"):
            extractor.extract("BTC/USDT", "1h")

    def test_extract_with_retry_success(self):
        """Test l'extraction avec réessai réussi."""
        mock_client = MagicMock()

        # Première tentative échoue, deuxième réussit
        mock_client.fetch_ohlcv.side_effect = [
            Exception("Temporarily unavailable"),
            [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]],
        ]

        extractor = OHLCVExtractor(mock_client, max_retries=2)

        # Doit réussir au deuxième essai
        result = extractor.extract("BTC/USDT", "1h")

        assert len(result) == 1
        assert mock_client.fetch_ohlcv.call_count == 2

    def test_extract_with_retry_failure(self):
        """Test l'extraction avec réessai échoué."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.side_effect = Exception("Persistent error")

        extractor = OHLCVExtractor(mock_client, max_retries=2)

        # Doit échouer après 2 tentatives
        with pytest.raises(
            ExtractionError, match="Échec d'extraction après 2 tentatives"
        ):
            extractor.extract("BTC/USDT", "1h")

        assert mock_client.fetch_ohlcv.call_count == 2

    def test_extract_with_custom_limit(self):
        """Test l'extraction avec une limite personnalisée."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [[1, 2, 3, 4, 5, 6]] * 50

        extractor = OHLCVExtractor(mock_client)

        result = extractor.extract("BTC/USDT", "1h", 50)

        mock_client.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1h", 50)
        assert len(result) == 50


class TestOHLCVExtractorExtractMultiple:
    """Tests pour la méthode extract_multiple."""

    def test_extract_multiple_success(self):
        """Test l'extraction multiple réussie."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [[1, 2, 3, 4, 5, 6]]

        extractor = OHLCVExtractor(mock_client)

        symbols = ["BTC/USDT", "ETH/USDT"]
        results = extractor.extract_multiple(symbols, "1h")

        assert len(results) == 2
        assert "BTC/USDT" in results
        assert "ETH/USDT" in results
        assert len(results["BTC/USDT"]) == 1
        assert len(results["ETH/USDT"]) == 1

    def test_extract_multiple_partial_failure(self):
        """Test l'extraction multiple avec échec partiel."""
        mock_client = MagicMock()

        # BTC réussit, ETH échoue
        def side_effect(symbol, *args):
            if symbol == "BTC/USDT":
                return [[1, 2, 3, 4, 5, 6]]
            else:
                raise Exception("Error")

        mock_client.fetch_ohlcv.side_effect = side_effect

        extractor = OHLCVExtractor(mock_client)

        symbols = ["BTC/USDT", "ETH/USDT"]
        results = extractor.extract_multiple(symbols, "1h")

        assert len(results) == 2
        assert results["BTC/USDT"] is not None
        assert results["ETH/USDT"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
