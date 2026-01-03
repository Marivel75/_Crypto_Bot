from sqlalchemy import create_engine
from src.config import settings

# Crée l'engine PostgreSQL avec les infos de settings.py
engine = create_engine(
    f"postgresql+psycopg2://{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

def get_engine():
    """Retourne l'engine SQLAlchemy pour PostgreSQL"""
    return engine
