# Base SQLAlchemy partagée pour les modèles Market Data

from sqlalchemy.ext.declarative import declarative_base

# Base partagée par tous les modèles market data
MarketDataBase = declarative_base()
