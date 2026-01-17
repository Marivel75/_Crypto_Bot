"""
Fichier de configuration pour les tests pytest.
Initialise la configuration et les fixtures communes.
"""

import pytest
import os
import sys

# Ajouter le chemin racine au path pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import config


def pytest_configure():
    """Configuration initiale pour tous les tests"""
    # S'assurer que la configuration est chargée
    global config
    config = config  # Déclencher l'initialisation si ce n'est pas déjà fait


@pytest.fixture(scope="session", autouse=True)
def setup_test_config():
    """Fixture pour configurer l'environnement de test"""
    # Créer un fichier de configuration de test minimal si nécessaire
    test_config = {
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "timeframes": ["1h", "4h"],
        "exchanges": ["binance"],
        "ticker": {
            "enabled": False,
            "snapshot_interval": 5,
            "runtime": 60,
            "cache_size": 100,
            "cache_cleanup_interval": 30
        },
        "scheduler": {
            "enabled": False,
            "schedule_time": "09:00"
        },
        "database": {
            "url": "sqlite:///data/processed/crypto_data.db",
            "timeout": 30
        }
    }
    
    # Mettre à jour la configuration globale avec les valeurs de test
    # Cela permet aux tests de fonctionner même sans fichier de config
    for key, value in test_config.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                config._config[key][subkey] = subvalue
        else:
            config._config[key] = value
    
    return config