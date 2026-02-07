"""
Tests unitaires pour l'OHLCVExtractor.
"""

import pytest
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etl.extractor import OHLCVExtractor, ExtractionError


class TestOHLCVExtractorInitialization:
    """Tests pour l'initialisation de l'extracteur."""
    
    def test_initialization_with_client(self):
        """Test l'initialisation avec un client mock."""
        mock_client = MagicMock()
        mock_client.__class__.__name__ = "MockClient"
        
        extractor = OHLCVExtractor(mock_client)
        
        assert extractor.client == mock_client
        assert extractor.exchange_name is None
    
    def test_initialization_with_exchange_name(self):
        """Test l'initialisation avec un nom d'exchange."""
        mock_client = MagicMock()
        extractor = OHLCVExtractor(mock_client, exchange_name="binance")
        
        assert extractor.exchange_name == "binance"


class TestOHLCVExtractorExtractOHLCVData:
    """Tests pour la méthode extract_ohlcv_data (nouvelle API)."""
    
    def test_extract_ohlcv_data_success(self):
        """Test l'extraction réussie avec la nouvelle API."""
        # Configuration du mock
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
            [1768298400000, 90050.0, 90150.0, 89950.0, 90100.0, 124.56],
        ]

        extractor = OHLCVExtractor(mock_client, exchange_name="binance")

        # Exécution avec la nouvelle API
        pairs = ["BTC/USDT"]
        result = extractor.extract_ohlcv_data(pairs, "1h", 100)

        # Vérifications
        assert isinstance(result, dict)
        assert len(result) == 1
        assert "BTC/USDT" in result
        
        df = result["BTC/USDT"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        
        # Vérifier que les colonnes de base sont présentes
        expected_base_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in expected_base_cols:
            assert col in df.columns
        
        # Vérifier que les métadonnées sont présentes
        assert "symbol" in df.columns
        assert "timeframe" in df.columns
        assert "exchange" in df.columns
        
        # Vérifier les valeurs des métadonnées
        assert (df["symbol"] == "BTC/USDT").all()
        assert (df["timeframe"] == "1h").all()
        assert (df["exchange"] == "binance").all()
        
        # Vérifier l'appel au client
        mock_client.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1h", limit=100)

    def test_extract_ohlcv_data_empty_data(self):
        """Test l'extraction quand aucune donnée n'est retournée."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = []

        extractor = OHLCVExtractor(mock_client, exchange_name="binance")

        # Doit retourner un DataFrame vide
        pairs = ["BTC/USDT"]
        result = extractor.extract_ohlcv_data(pairs, "1h")
        
        assert isinstance(result, dict)
        assert "BTC/USDT" in result
        assert result["BTC/USDT"].empty

    def test_extract_ohlcv_data_exception(self):
        """Test l'extraction quand une exception est levée."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.side_effect = Exception("API Error")

        extractor = OHLCVExtractor(mock_client, exchange_name="binance")

        # Doit retourner un DataFrame vide en cas d'exception
        pairs = ["BTC/USDT"]
        result = extractor.extract_ohlcv_data(pairs, "1h")
        
        assert isinstance(result, dict)
        assert "BTC/USDT" in result
        assert result["BTC/USDT"].empty

    def test_extract_ohlcv_data_multiple_pairs(self):
        """Test l'extraction pour plusieurs paires."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
        ]

        extractor = OHLCVExtractor(mock_client, exchange_name="binance")

        pairs = ["BTC/USDT", "ETH/USDT"]
        result = extractor.extract_ohlcv_data(pairs, "1h", 100)

        # Vérifications
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        
        # Les deux DataFrames doivent avoir les mêmes données
        assert len(result["BTC/USDT"]) == 1
        assert len(result["ETH/USDT"]) == 1
        
        # Vérifier que fetch_ohlcv a été appelé pour chaque paire
        calls = mock_client.fetch_ohlcv.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ("BTC/USDT", "1h")
        assert calls[1][0] == ("ETH/USDT", "1h")

    def test_extract_ohlcv_data_with_custom_limit(self):
        """Test l'extraction avec une limite personnalisée."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [[1, 2, 3, 4, 5, 6]] * 50

        extractor = OHLCVExtractor(mock_client, exchange_name="binance")

        pairs = ["BTC/USDT"]
        result = extractor.extract_ohlcv_data(pairs, "1h", 50)

        df = result["BTC/USDT"]
        assert len(df) == 50
        mock_client.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1h", limit=50)

    def test_extract_ohlcv_data_without_exchange_name(self):
        """Test l'extraction sans nom d'exchange."""
        mock_client = MagicMock()
        mock_client.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
        ]

        extractor = OHLCVExtractor(mock_client)  # Sans exchange_name

        pairs = ["BTC/USDT"]
        result = extractor.extract_ohlcv_data(pairs, "1h")

        df = result["BTC/USDT"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        # exchange_name devrait être None
        assert (df["exchange"].isna()).all()