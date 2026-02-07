"""
Module pour charger les variables d'environnement sensibles depuis le fichier .env.
Gère les configurations pour SQLite (développement) et Supabase (production).
"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Environnement (développement ou production)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Clés API des exchanges
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")
COINBASE_API_PASSPHRASE = os.getenv("COINBASE_API_PASSPHRASE")

# Clé API pour les news
CRYPTORANK_API_KEY = os.getenv("CRYPTORANK_API_KEY")

# Configuration de la base de données
# Variables exposées pour importation dans d'autres modules
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")  # URL complète avec mot de passe
SUPABASE_API_URL = os.getenv("SUPABASE_API_URL")
SUPABASE_ANON_API_KEY = os.getenv(
    "SUPABASE_ANON_API_KEY"
)  # Clé publique pour l'API REST (optionnel)
POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD"
)  # Optionnel, si besoin séparément
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/processed/crypto_data.db")

# Configuration spécifique à l'environnement
if ENVIRONMENT == "production":
    # Vérification que les variables Supabase sont définies
    if not SUPABASE_DB_URL:
        raise ValueError("SUPABASE_DB_URL must be set in production environment")
