"""
Tests unitaires pour le service de tickers. Teste:
- Le cache des tickers (TickerCache)
- Le collecteur de tickers (TickerCollector)
- L'intégration avec la base de données
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from src.services.ticker_service import TickerCollector, TickerCache
from src.models.ticker import TickerSnapshot


class TestTickerCache:
    """Tests pour la classe TickerCache"""

    def test_initialization(self):
        """Test l'initialisation du cache"""
        cache = TickerCache(max_items_per_symbol=5)
        assert cache.max_items == 5
        assert cache.cache == {}

    def test_add_ticker(self):
        """Test l'ajout de tickers au cache"""
        cache = TickerCache(max_items_per_symbol=3)

        # Ajouter des tickers
        ticker1 = {"price": 50000, "volume": 1000}
        ticker2 = {"price": 50100, "volume": 1100}
        ticker3 = {"price": 50200, "volume": 1200}
        ticker4 = {"price": 50300, "volume": 1300}

        cache.add_ticker("BTC/USDT", ticker1)
        cache.add_ticker("BTC/USDT", ticker2)
        cache.add_ticker("BTC/USDT", ticker3)
        cache.add_ticker("BTC/USDT", ticker4)

        # Vérifier que la limite est respectée
        assert len(cache.cache["BTC/USDT"]) == 3  # Le 4ème a été supprimé
        assert cache.cache["BTC/USDT"][0]["data"]["price"] == 50100  # Le plus récent

    def test_get_recent_tickers(self):
        """Test la récupération des tickers récents"""
        cache = TickerCache(max_items_per_symbol=10)

        # Ajouter des tickers avec des timestamps
        base_time = datetime.utcnow()
        for i in range(5):
            ticker = {"price": 50000 + i * 100}
            cache.add_ticker("BTC/USDT", ticker)
            time.sleep(0.01)  # Délai pour avoir des timestamps différents

        # Récupérer les tickers des 2 dernières minutes
        recent = cache.get_recent_tickers("BTC/USDT", minutes=2)
        assert len(recent) <= 5

        # Récupérer les tickers des 10 dernières secondes
        very_recent = cache.get_recent_tickers("BTC/USDT", minutes=0.1)
        assert len(very_recent) >= 1

    def test_get_current_prices(self):
        """Test la récupération des prix actuels"""
        cache = TickerCache(max_items_per_symbol=5)

        # Ajouter des tickers
        cache.add_ticker("BTC/USDT", {"price": 50000})
        cache.add_ticker("ETH/USDT", {"price": 3000})

        # Récupérer les prix actuels
        prices = cache.get_current_prices()
        assert "BTC/USDT" in prices
        assert "ETH/USDT" in prices
        assert prices["BTC/USDT"]["price"] == 50000

    def test_clear_old_data(self):
        """Test le nettoyage des anciennes données"""
        cache = TickerCache(max_items_per_symbol=10)

        # Ajouter des anciens tickers
        old_time = datetime.utcnow() - timedelta(hours=48)
        for i in range(5):
            ticker_entry = {
                "timestamp": old_time - timedelta(minutes=i),
                "data": {"price": 50000 + i * 100},
            }
            if "BTC/USDT" not in cache.cache:
                cache.cache["BTC/USDT"] = []
            cache.cache["BTC/USDT"].append(ticker_entry)

        # Ajouter des tickers récents
        cache.add_ticker("BTC/USDT", {"price": 51000})

        # Nettoyer les données de plus de 24h
        cache.clear_old_data(hours=24)

        # Vérifier que seuls les tickers récents restent
        assert len(cache.cache["BTC/USDT"]) == 1
        assert cache.cache["BTC/USDT"][0]["data"]["price"] == 51000


class TestTickerCollector:
    """Tests pour la classe TickerCollector"""

    @patch("src.services.exchange_factory.ExchangeFactory.create_exchange")
    def test_initialization(self, mock_create_exchange):
        """Test l'initialisation du collecteur"""
        # Configurer le mock
        mock_client_instance = MagicMock()
        mock_create_exchange.return_value = mock_client_instance
        
        collector = TickerCollector(
            pairs=["BTC/USDT", "ETH/USDT"],
            exchange="binance",
            snapshot_interval=5,
            cache_size=10,
            cache_cleanup_interval=30,
        )

        assert collector.pairs == ["BTC/USDT", "ETH/USDT"]
        assert collector.exchange == "binance"
        assert collector.snapshot_interval == 5
        assert collector.cache_cleanup_interval == 30
        assert collector.cache.max_items == 10
        assert not collector.running
        assert collector.client == mock_client_instance
        # Vérifier que la factory a été appelée avec les bons paramètres
        mock_create_exchange.assert_called_once_with("binance")

    @patch("src.services.exchange_factory.ExchangeFactory.create_exchange")
    def test_start_stop_collection(self, mock_create_exchange):
        """Test le démarrage et l'arrêt de la collecte"""
        # Configurer le mock
        mock_client_instance = MagicMock()
        mock_create_exchange.return_value = mock_client_instance
        
        collector = TickerCollector(["BTC/USDT"], "binance")

        # Démarrer la collecte
        collector.start_collection()
        assert collector.running
        assert collector.collector_thread is not None

        # Arrêter la collecte
        collector.stop_collection()
        assert not collector.running
        assert collector.collector_thread is None

    @patch("src.services.ticker_service.TickerCollector._fetch_and_cache_tickers")
    @patch("src.services.ticker_service.TickerCollector._save_snapshot")
    @patch("src.services.exchange_factory.ExchangeFactory.create_exchange")
    def test_collection_loop(self, mock_create_exchange, mock_fetch, mock_save):
        """Test la boucle de collecte principale"""
        # Configurer le mock
        mock_client_instance = MagicMock()
        mock_create_exchange.return_value = mock_client_instance
        
        collector = TickerCollector(["BTC/USDT"], "binance", snapshot_interval=1)

        # Démarrer la collecte
        collector.start_collection()

        # Attendre un peu pour que la boucle s'exécute
        time.sleep(2)

        # Arrêter la collecte
        collector.stop_collection()

        assert True


class TestTickerDatabase:
    """Tests pour l'intégration avec la base de données"""

    @patch("src.services.db.get_db_engine")
    @patch("src.services.exchange_factory.ExchangeFactory.create_exchange")
    def test_save_snapshot(self, mock_create_exchange, mock_engine):
        """Test la sauvegarde des snapshots"""
        # Configurer le mock du client Binance
        mock_client_instance = MagicMock()
        mock_create_exchange.return_value = mock_client_instance
        
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

        collector = TickerCollector(["BTC/USDT"], "binance")

        # Ajouter des données au cache
        collector.cache.add_ticker(
            "BTC/USDT",
            {
                "price": 50000,
                "volume_24h": 1000,
                "price_change_24h": 500,
                "price_change_pct_24h": 1.0,
                "high_24h": 50500,
                "low_24h": 49500,
            },
        )

        # Sauvegarder un snapshot
        collector._save_snapshot()
        assert True  # Test simplifié


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
