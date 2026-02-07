"""
Tests unitaires pour le OHLCVCollector.
Teste la validation des entrées, l'initialisation et les méthodes principales.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.ohlcv_collector import OHLCVCollector


class TestOHLCVCollectorInitialization:
    """Tests pour l'initialisation du OHLCVCollector."""

    def test_initialization_with_valid_parameters(self):
        """Test l'initialisation avec des paramètres valides, utilisation de l'exchange Binance."""
        pairs = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["1h", "4h"]

        # Mock de l'ExchangeFactory et du DataValidator pour éviter les appels API réels
        with patch(
            "src.collectors.ohlcv_collector.ExchangeFactory"
        ) as mock_factory, patch(
            "src.collectors.ohlcv_collector.DataValidator0HCLV"
        ) as mock_validator:
            mock_factory.create_exchange.return_value = MagicMock()
            mock_validator.return_value = MagicMock()

            collector = OHLCVCollector(pairs, timeframes, "binance")

            assert collector.pairs == pairs
            assert collector.timeframes == timeframes
            assert collector.exchange == "binance"
            assert isinstance(collector.client, MagicMock)
            assert isinstance(collector.data_validator, MagicMock)

    def test_initialization_with_empty_pairs(self):
        """Test l'initialisation avec une liste de paires vide."""
        with pytest.raises(
            ValueError,
            match="Les listes de paires et timeframes ne peuvent pas être vides",
        ):
            OHLCVCollector([], ["1h"], "binance")

    def test_initialization_with_empty_timeframes(self):
        """Test l'initialisation avec une liste de timeframes vide."""
        with pytest.raises(
            ValueError,
            match="Les listes de paires et timeframes ne peuvent pas être vides",
        ):
            OHLCVCollector(["BTC/USDT"], [], "binance")

    def test_initialization_with_invalid_pair_type(self):
        """Test l'initialisation avec un type de paire invalide."""
        with pytest.raises(
            ValueError,
            match="Toutes les paires doivent être des chaînes de caractères non vides",
        ):
            OHLCVCollector([123, "ETH/USDT"], ["1h"], "binance")

    def test_initialization_with_invalid_timeframe_type(self):
        """Test l'initialisation avec un type de timeframe invalide."""
        with pytest.raises(
            ValueError,
            match="Tous les timeframes doivent être des chaînes de caractères non vides",
        ):
            OHLCVCollector(["BTC/USDT"], [123, "4h"], "binance")

    def test_initialization_with_unsupported_exchange(self):
        """Test l'initialisation avec un exchange non supporté."""
        with pytest.raises(ValueError, match="Exchange non supporté"):
            OHLCVCollector(["BTC/USDT"], ["1h"], "unsupported_exchange")

    def test_initialization_with_kraken(self):
        """Test l'initialisation avec Kraken."""
        with patch("src.collectors.ohlcv_collector.ExchangeFactory") as mock_factory:
            mock_factory.create_exchange.return_value = MagicMock()

            collector = OHLCVCollector(["BTC/USD"], ["1h"], "kraken")

            assert collector.exchange == "kraken"
            assert isinstance(collector.client, MagicMock)

    def test_initialization_with_coinbase(self):
        """Test l'initialisation avec Coinbase."""
        with patch("src.collectors.ohlcv_collector.ExchangeFactory") as mock_factory:
            mock_factory.create_exchange.return_value = MagicMock()

            collector = OHLCVCollector(["BTC/USD"], ["1h"], "coinbase")

            assert collector.exchange == "coinbase"
            assert isinstance(collector.client, MagicMock)


class TestOHLCVCollectorValidation:
    """Tests pour la validation des données."""

    def test_validate_empty_pair_in_list(self):
        """Test la validation avec une paire vide dans la liste."""
        with pytest.raises(
            ValueError,
            match="Toutes les paires doivent être des chaînes de caractères non vides",
        ):
            OHLCVCollector(["BTC/USDT", ""], ["1h"], "binance")

    def test_validate_empty_timeframe_in_list(self):
        """Test la validation avec un timeframe vide dans la liste."""
        with pytest.raises(
            ValueError,
            match="Tous les timeframes doivent être des chaînes de caractères non vides",
        ):
            OHLCVCollector(["BTC/USDT"], ["1h", ""], "binance")

    def test_validate_whitespace_pair(self):
        """Test la validation avec une paire contenant uniquement des espaces."""
        with pytest.raises(
            ValueError,
            match="Toutes les paires doivent être des chaînes de caractères non vides",
        ):
            OHLCVCollector(["BTC/USDT", "   "], ["1h"], "binance")


class TestOHLCVCollectorFetchAndStore:
    """Tests pour la méthode fetch_and_store."""

    @patch("src.collectors.ohlcv_collector.ExchangeClient")
    @patch("src.collectors.ohlcv_collector.ExchangeFactory")
    @patch("src.collectors.ohlcv_collector.DataValidator0HCLV")
    @patch("pandas.DataFrame.to_sql")
    def test_fetch_and_store_success(
        self, mock_to_sql, mock_validator, mock_factory, mock_exchange_client
    ):
        """Test le succès de fetch_and_store avec le pipeline ETL."""
        # Configuration du mock pour le constructeur
        mock_client_constructor = MagicMock()
        mock_factory.create_exchange.return_value = mock_client_constructor

        # Configuration du mock
        mock_client_instance = MagicMock()
        mock_client_instance.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
            [1768298400000, 90050.0, 90150.0, 89950.0, 90100.0, 124.56],
        ]

        # Configuration du mock du context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client_instance
        mock_context.__exit__.return_value = None
        mock_exchange_client.return_value = mock_context

        # Configuration du mock du valideur - utiliser un valideur réel pour le test
        from src.quality.validator import DataValidator0HCLV

        real_validator = DataValidator0HCLV()
        mock_validator.return_value = real_validator

        # Configuration du mock to_sql pour le loader
        mock_to_sql.return_value = 2

        collector = OHLCVCollector(["BTC/USDT"], ["1h"], "binance")

        # Exécuter la méthode
        collector.fetch_and_store()

        # Vérifier que fetch_ohlcv a été appelé correctement
        mock_client_instance.fetch_ohlcv.assert_called_once_with(
            "BTC/USDT", "1h", limit=100
        )

    @patch("src.collectors.ohlcv_collector.ExchangeClient")
    @patch("src.collectors.ohlcv_collector.ExchangeFactory")
    @patch("pandas.DataFrame.to_sql")
    def test_fetch_and_store_with_duplicate_data(
        self, mock_to_sql, mock_factory, mock_exchange_client
    ):
        """Test la gestion des doublons dans fetch_and_store."""
        # Configuration du mock pour le constructeur
        mock_client_constructor = MagicMock()
        mock_factory.create_exchange.return_value = mock_client_constructor

        mock_client_instance = MagicMock()
        mock_client_instance.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]
        ]

        # Configuration du mock du context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client_instance
        mock_context.__exit__.return_value = None
        mock_exchange_client.return_value = mock_context

        # Configurer to_sql pour simuler un IntegrityError (doublon)
        from sqlalchemy.exc import IntegrityError

        mock_to_sql.side_effect = IntegrityError("mock", "mock", "Duplicate entry")

        collector = OHLCVCollector(["BTC/USDT"], ["1h"], "binance")

        # Exécuter la méthode
        collector.fetch_and_store()

        # Vérifier que to_sql a été appelé
        assert mock_to_sql.called
        # Vérifier que l'erreur a été gérée (pas de propagation)

    @patch("src.collectors.ohlcv_collector.ExchangeClient")
    @patch("src.collectors.ohlcv_collector.ExchangeFactory")
    @patch("src.collectors.ohlcv_collector.DataValidator0HCLV")
    @patch("pandas.DataFrame.to_sql")
    def test_fetch_and_store_with_invalid_data(
        self, mock_to_sql, mock_validator, mock_factory, mock_exchange_client
    ):
        """Test que les données invalides ne sont pas sauvegardées."""
        # Configuration du mock pour le constructeur
        mock_client_constructor = MagicMock()
        mock_factory.create_exchange.return_value = mock_client_constructor

        # Configuration du mock client
        mock_client_instance = MagicMock()
        mock_client_instance.fetch_ohlcv.return_value = [
            [1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45],
        ]

        # Configuration du mock du context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client_instance
        mock_context.__exit__.return_value = None
        mock_exchange_client.return_value = mock_context

        # Configuration du mock valideur pour retourner des données invalides
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_ohlcv_values.return_value = (
            False,
            {
                "valid_rows": 0,
                "total_rows": 1,
                "errors": ["Prix négatif détecté", "Volume invalide"],
                "warnings": [],
            },
        )
        mock_validator.return_value = mock_validator_instance

        collector = OHLCVCollector(["BTC/USDT"], ["1h"], "binance")

        # Exécuter la méthode
        collector.fetch_and_store()

        # Vérifier que la validation a été appelée
        mock_validator_instance.validate_ohlcv_values.assert_called_once()

        # Vérifier que to_sql n'a pas été appelé (données invalides)
        assert not mock_to_sql.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
